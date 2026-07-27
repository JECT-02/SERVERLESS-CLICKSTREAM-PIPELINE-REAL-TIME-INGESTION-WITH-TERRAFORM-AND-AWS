import polars as pl
from pathlib import Path

RAW_PATH = Path('data/raw/all_events.ndjson')
BRONZE_PATH = Path('data/processed/bronze.parquet')
SILVER_PATH = Path('data/processed/silver.parquet')
GOLD_PATH = Path('data/processed/gold.parquet')

IDLE_VELOCITY_THRESHOLD = 5.0
EXIT_INTENT_Y_UPPER = 100
EXIT_INTENT_VELOCITY_THRESHOLD = 200.0
HEARTBEAT_INTERVAL_S = 0.25


BRONZE_PATH.parent.mkdir(parents=True, exist_ok=True)


def bronze_layer():
    df = pl.read_ndjson(RAW_PATH, infer_schema_length=None)

    df = df.with_columns([
        pl.col('timestamp').str.strptime(
            pl.Datetime, '%Y-%m-%dT%H:%M:%S%.fZ'
        ).alias('event_timestamp'),
        pl.col('mouse_x').cast(pl.Float64, strict=False).fill_null(0.0),
        pl.col('mouse_y').cast(pl.Float64, strict=False).fill_null(0.0),
        pl.col('cart_value').cast(pl.Float64, strict=False).fill_null(0.0),
        pl.col('product_count').cast(pl.Int64, strict=False).fill_null(0),
        pl.col('mouse_click_count').cast(pl.Int64, strict=False).fill_null(0),
        pl.col('device').cast(pl.Utf8, strict=False).fill_null('desktop'),
        pl.col('page').cast(pl.Utf8, strict=False).fill_null('catalog'),
        pl.col('shipping_option_selected').cast(pl.Utf8, strict=False).fill_null('standard'),
        pl.col('event_type').cast(pl.Utf8),
        pl.col('session_id').cast(pl.Utf8),
        pl.col('user_id').cast(pl.Utf8),
        pl.col('product_quantities').cast(pl.Utf8, strict=False).fill_null('{}'),
    ])

    df = df.with_columns([
        pl.col('event_timestamp').dt.year().cast(pl.Utf8).alias('year'),
        pl.col('event_timestamp').dt.month().cast(pl.Utf8).str.zfill(2).alias('month'),
        pl.col('event_timestamp').dt.day().cast(pl.Utf8).str.zfill(2).alias('day'),
    ])

    df.write_parquet(BRONZE_PATH)
    return df.shape[0]


def silver_layer():
    df = pl.read_parquet(BRONZE_PATH)
    df = df.sort('event_timestamp')

    hb = df.filter(pl.col('event_type') == 'heartbeat')

    hb = hb.with_columns([
        pl.col('mouse_x').shift(1).over('session_id').alias('prev_mouse_x'),
        pl.col('mouse_y').shift(1).over('session_id').alias('prev_mouse_y'),
        pl.col('event_timestamp').shift(1).over('session_id').alias('prev_timestamp'),
        pl.col('cart_value').shift(1).over('session_id').alias('prev_cart_value'),
        pl.col('shipping_option_selected').shift(1).over('session_id').alias('prev_shipping'),
    ])

    hb = hb.with_columns([
        (pl.col('mouse_x') - pl.col('prev_mouse_x')).alias('dx'),
        (pl.col('mouse_y') - pl.col('prev_mouse_y')).alias('dy'),
        (pl.col('event_timestamp') - pl.col('prev_timestamp'))
        .dt.total_seconds().alias('delta_time_s'),
        (pl.col('cart_value') - pl.col('prev_cart_value')).alias('cart_delta'),
        (pl.col('shipping_option_selected') != pl.col('prev_shipping'))
        .alias('shipping_changed'),
    ])

    hb = hb.with_columns([
        pl.when(
            pl.col('delta_time_s').is_null() | (pl.col('delta_time_s') <= 0)
        ).then(HEARTBEAT_INTERVAL_S).otherwise(pl.col('delta_time_s')).alias('delta_time_s'),
        pl.col('dx').fill_null(0.0),
        pl.col('dy').fill_null(0.0),
        pl.col('cart_delta').fill_null(0.0),
        pl.col('shipping_changed').fill_null(False),
    ])

    hb = hb.with_columns([
        (pl.col('dx') ** 2 + pl.col('dy') ** 2).sqrt().alias('mouse_distance'),
    ])

    hb = hb.with_columns([
        pl.when(pl.col('delta_time_s') > 0)
        .then(pl.col('mouse_distance') / pl.col('delta_time_s'))
        .otherwise(0.0).alias('velocity_px_s'),
    ])

    hb = hb.with_columns([
        (pl.col('velocity_px_s') - pl.col('velocity_px_s').shift(1).over('session_id'))
        .fill_null(0.0).alias('acceleration_px_s2'),
        (pl.col('velocity_px_s') < IDLE_VELOCITY_THRESHOLD).alias('is_idle'),
        ((pl.col('mouse_y') < EXIT_INTENT_Y_UPPER)
         & (pl.col('velocity_px_s') > EXIT_INTENT_VELOCITY_THRESHOLD)).alias('is_exit_intent'),
        ((pl.col('dx') == 0) & (pl.col('dy') == 0)).alias('is_dwell'),
    ])

    hb = hb.with_columns([
        pl.when(pl.col('is_idle'))
        .then(pl.col('delta_time_s') * 1000).otherwise(0).alias('idle_ms_segment'),
        pl.when(pl.col('is_dwell'))
        .then(pl.col('delta_time_s') * 1000).otherwise(0).alias('dwell_ms_segment'),
        pl.col('shipping_changed').cast(pl.Int64),
    ])

    hb.write_parquet(SILVER_PATH)
    return hb.shape[0]


def gold_layer():
    hb = pl.read_parquet(SILVER_PATH)
    all_events = pl.read_parquet(BRONZE_PATH)

    all_events = all_events.sort('event_timestamp').with_columns([
        pl.col('shipping_option_selected').shift(1).over('session_id').alias('prev_shp'),
        pl.col('page').shift(1).over('session_id').alias('prev_page'),
    ]).with_columns([
        (pl.col('shipping_option_selected') != pl.col('prev_shp'))
        .fill_null(False).cast(pl.Int64).alias('ship_switch'),
        ((pl.col('page') == 'cart') & (pl.col('prev_page') == 'checkout'))
        .fill_null(False).cast(pl.Int64).alias('page_regression'),
    ])

    hb_agg = hb.group_by('session_id').agg([
        pl.col('event_timestamp').first().alias('session_start'),
        pl.col('event_timestamp').last().alias('session_end'),
        pl.len().alias('heartbeat_count'),
        pl.col('velocity_px_s').mean().alias('velocity_avg'),
        pl.col('velocity_px_s').max().alias('velocity_max'),
        pl.col('velocity_px_s').std().alias('velocity_std'),
        pl.col('acceleration_px_s2').mean().alias('acceleration_avg'),
        pl.col('acceleration_px_s2').max().alias('acceleration_max'),
        pl.col('idle_ms_segment').sum().alias('total_idle_ms'),
        pl.col('mouse_distance').sum().alias('total_distance_px'),
        pl.col('is_exit_intent').sum().alias('exit_intent_count'),
        pl.col('dwell_ms_segment').sum().alias('total_dwell_ms'),
        pl.col('is_dwell').sum().alias('dwell_event_count'),
        pl.col('mouse_click_count').last().alias('last_click_count'),
        pl.col('mouse_click_count').first().alias('first_click_count'),
        pl.col('cart_value').max().alias('cart_value_max'),
        pl.col('cart_value').mean().alias('cart_value_avg'),
        pl.col('cart_delta').sum().alias('cart_delta_total'),
        pl.col('shipping_changed').sum().alias('shipping_switches'),
    ])

    hb_agg = hb_agg.with_columns([
        (pl.col('session_end') - pl.col('session_start'))
        .dt.total_seconds().alias('session_duration_s'),
        (pl.col('last_click_count') - pl.col('first_click_count'))
        .clip(0, None).alias('total_clicks'),
    ])

    hb_agg = hb_agg.with_columns([
        pl.when(pl.col('session_duration_s') > 0)
        .then(pl.col('total_clicks') / pl.col('session_duration_s'))
        .otherwise(0.0).alias('click_frequency'),
        pl.when(pl.col('session_duration_s') > 0)
        .then(pl.col('total_idle_ms') / (pl.col('session_duration_s') * 1000))
        .otherwise(0.0).alias('idle_ratio'),
    ])

    all_agg = all_events.group_by('session_id').agg([
        pl.len().alias('total_events'),
        pl.col('device').first().alias('device'),
        pl.col('user_id').first().alias('user_id'),
        pl.col('product_count').max().alias('product_count_max'),
        pl.col('event_type').filter(pl.col('event_type') == 'add_to_cart').len()
        .alias('add_to_cart_count'),
        pl.col('event_type').filter(pl.col('event_type') == 'remove_from_cart').len()
        .alias('remove_from_cart_count'),
        pl.col('event_type').filter(pl.col('event_type') == 'start_checkout').len()
        .alias('checkout_count'),
        pl.col('event_type').filter(pl.col('event_type') == 'view_product').len()
        .alias('view_product_count'),
        (pl.col('event_type') == 'purchase').any().alias('has_purchase'),
        (pl.col('event_type') == 'abandon').any().alias('has_abandon'),
        pl.col('ship_switch').sum().alias('shipping_switches_all'),
        pl.col('page_regression').sum().alias('page_regression_count'),
    ])

    checkout_events = all_events.filter(pl.col('page') == 'checkout')
    checkout_agg = checkout_events.group_by('session_id').agg([
        pl.col('event_timestamp').min().alias('checkout_first_ts'),
        pl.col('event_timestamp').max().alias('checkout_last_ts'),
    ])

    gold = hb_agg.join(all_agg, on='session_id', how='full').join(
        checkout_agg, on='session_id', how='left'
    )

    gold = gold.with_columns([
        pl.col('heartbeat_count').fill_null(0),
        pl.col('total_events').fill_null(0),
        pl.col('session_duration_s').fill_null(0.0),
        pl.col('has_purchase').fill_null(False),
        pl.col('has_abandon').fill_null(False),
        pl.col('page_regression_count').fill_null(0),
        pl.col('shipping_switches_all').fill_null(0),
        pl.col('device').fill_null('desktop'),
        pl.col('user_id').fill_null(''),
        pl.col('product_count_max').fill_null(0),
        pl.col('add_to_cart_count').fill_null(0),
        pl.col('remove_from_cart_count').fill_null(0),
        pl.col('checkout_count').fill_null(0),
        pl.col('view_product_count').fill_null(0),
    ])

    gold = gold.with_columns([
        (pl.col('has_abandon') & ~pl.col('has_purchase')).alias('abandoned'),
        pl.when(
            pl.col('checkout_last_ts').is_not_null()
            & pl.col('checkout_first_ts').is_not_null()
        ).then(
            (pl.col('checkout_last_ts') - pl.col('checkout_first_ts'))
            .dt.total_seconds() * 1000
        ).otherwise(0).alias('payment_hesitation_ms'),
        pl.col('velocity_avg').fill_null(0.0),
        pl.col('velocity_max').fill_null(0.0),
        pl.col('velocity_std').fill_null(0.0),
        pl.col('acceleration_avg').fill_null(0.0),
        pl.col('acceleration_max').fill_null(0.0),
        pl.col('total_idle_ms').fill_null(0),
        pl.col('total_distance_px').fill_null(0.0),
        pl.col('exit_intent_count').fill_null(0),
        pl.col('total_dwell_ms').fill_null(0),
        pl.col('dwell_event_count').fill_null(0),
        pl.col('click_frequency').fill_null(0.0),
        pl.col('idle_ratio').fill_null(0.0),
        pl.col('cart_value_max').fill_null(0.0),
        pl.col('cart_value_avg').fill_null(0.0),
        pl.col('cart_delta_total').fill_null(0.0),
        pl.col('shipping_switches').fill_null(0),
        pl.col('total_clicks').fill_null(0),
    ])

    gold = gold.with_columns([
        pl.col('abandoned').cast(pl.Int64).alias('abandoned'),
        pl.col('has_purchase').cast(pl.Int64),
        pl.col('has_abandon').cast(pl.Int64),
        pl.col('payment_hesitation_ms').cast(pl.Int64),
    ])

    gold = gold.filter((pl.col('has_purchase') == 1) | (pl.col('has_abandon') == 1))

    gold = gold.with_columns([
        pl.when(pl.col('session_duration_s') > 0)
        .then(pl.col('total_events') / pl.col('session_duration_s') * 60)
        .otherwise(0.0).alias('events_per_minute'),
    ])

    gold.write_parquet(GOLD_PATH)
    return gold.shape[0]


def run_pipeline():
    return {
        'bronze_rows': bronze_layer(),
        'silver_rows': silver_layer(),
        'gold_rows': gold_layer(),
    }


if __name__ == '__main__':
    run_pipeline()
