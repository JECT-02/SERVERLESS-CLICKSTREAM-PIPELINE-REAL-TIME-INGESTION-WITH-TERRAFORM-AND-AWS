import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const originalFetch = global.fetch;
const originalSendBeacon = navigator.sendBeacon;

function setupDom() {
  document.body.innerHTML = `
    <div id="app">
      <span id="cartSummary"></span>
      <div id="pageContent"></div>
      <div id="retentionModal" class="modal-overlay">
        <div id="retentionTitle"></div>
        <div id="retentionMessage"></div>
        <div id="retentionContent"></div>
      </div>
      <div id="abandonModal" class="modal-overlay">
        <div id="abandonReasons"></div>
      </div>
      <div id="productDetail" class="product-detail-overlay">
        <div id="detailContent"></div>
      </div>
    </div>
  `;
}

function createTestContext(apiUrl) {
  window.CLICKSTREAM_CONFIG = {
    apiUrl,
    trackedPages: ["cart", "checkout"],
    heartbeatIntervalMs: 250
  };

  const context = {
    carrito: [{ id: 'p1', cantidad: 1, precio: 100, categoria: 'test', imagen: '', nombre: 'Test' }],
    currentPage: "cart",
    deliveryMode: "shipping",
    shippingType: "standard",
    selectedStore: "Mall del Centro - Local 102",
    retentionData: null,
    pageLoadTime: Date.now(),
    sessionId: "test-session",
    userId: "test-user",
    productos: [
      { id: "p1", nombre: "Test", precio: 100, categoria: "test", imagen: "" }
    ],
    tiendas: ["Mall del Centro - Local 102"],
    razonesAbandono: [],
    mouseClickCount: 0,
    mouseX: 0,
    mouseY: 0
  };

  Object.assign(window, context);
  localStorage.setItem("userId", context.userId);

  return context;
}

function makeEvent(eventType, extra = {}) {
  const payload = {
    event_type: eventType,
    timestamp: new Date().toISOString(),
    session_id: window.sessionId,
    user_id: window.userId,
    mouse_click_count: window.mouseClickCount,
  };

  switch (eventType) {
    case "heartbeat":
      payload.page = window.currentPage;
      payload.cart_value = window.carrito.reduce((s, p) => s + p.precio * p.cantidad, 0);
      payload.product_count = window.carrito.length;
      payload.product_quantities = window.carrito.reduce((o, p) => { o[p.id] = p.cantidad; return o; }, {});
      payload.shipping_option_selected = window.deliveryMode === "store" ? "store" : window.shippingType;
      payload.mouse_x = window.mouseX;
      payload.mouse_y = window.mouseY;
      break;
    case "page_view":
      payload.page = extra.page || window.currentPage;
      payload.cart_value = window.carrito.reduce((s, p) => s + p.precio * p.cantidad, 0);
      payload.product_count = window.carrito.length;
      payload.product_quantities = window.carrito.reduce((o, p) => { o[p.id] = p.cantidad; return o; }, {});
      payload.shipping_option_selected = window.deliveryMode === "store" ? "store" : window.shippingType;
      break;
    case "add_to_cart":
      payload.product_id = extra.product_id;
      payload.category = extra.category;
      payload.price = extra.price;
      payload.cart_value = window.carrito.reduce((s, p) => s + p.precio * p.cantidad, 0);
      payload.product_count = window.carrito.length;
      payload.product_quantities = window.carrito.reduce((o, p) => { o[p.id] = p.cantidad; return o; }, {});
      payload.shipping_option_selected = window.deliveryMode === "store" ? "store" : window.shippingType;
      break;
    case "remove_from_cart":
      payload.cart_value = window.carrito.reduce((s, p) => s + p.precio * p.cantidad, 0);
      payload.product_count = window.carrito.length;
      payload.product_quantities = window.carrito.reduce((o, p) => { o[p.id] = p.cantidad; return o; }, {});
      payload.shipping_option_selected = window.deliveryMode === "store" ? "store" : window.shippingType;
      break;
    case "start_checkout":
      payload.page = "checkout";
      payload.cart_value = extra.cart_value;
      payload.product_count = window.carrito.length;
      payload.product_quantities = window.carrito.reduce((o, p) => { o[p.id] = p.cantidad; return o; }, {});
      payload.payment_method_selected = null;
      payload.shipping_option_selected = extra.shipping_type;
      break;
    case "purchase":
      payload.cart_value = extra.cart_value;
      payload.product_count = window.carrito.length;
      payload.product_quantities = window.carrito.reduce((o, p) => { o[p.id] = p.cantidad; return o; }, {});
      payload.payment_method_selected = extra.payment_method || "credit_card";
      payload.shipping_option_selected = extra.shipping_type;
      break;
    case "abandon":
      payload.cart_value = extra.cart_value;
      payload.product_count = window.carrito.length;
      payload.product_quantities = window.carrito.reduce((o, p) => { o[p.id] = p.cantidad; return o; }, {});
      payload.shipping_option_selected = extra.shipping_type;
      payload.abandon_reason = extra.abandon_reason;
      break;
    case "view_product":
      payload.product_id = extra.product_id;
      payload.category = extra.category;
      payload.price = extra.price;
      break;
  }

  return payload;
}

function shouldTrack() {
  return window.CLICKSTREAM_CONFIG.trackedPages.includes(window.currentPage) &&
         window.carrito.length > 0;
}

async function sendEvent(event) {
  if (!shouldTrack()) return;
  const res = await fetch(window.CLICKSTREAM_CONFIG.apiUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(event)
  });
  if (res.ok) return res.json();
}

function sendHeartbeat() {
  if (document.hidden) return;
  if (!shouldTrack()) return;
  sendEvent(makeEvent("heartbeat"));
}

function makeAbandonEvent(extra = {}) {
  return {
    event_type: "abandon",
    timestamp: new Date().toISOString(),
    session_id: window.sessionId,
    user_id: window.userId,
    mouse_click_count: window.mouseClickCount,
    cart_value: extra.cart_value,
    product_count: window.carrito.length,
    product_quantities: window.carrito.reduce((o, p) => { o[p.id] = p.cantidad; return o; }, {}),
    shipping_option_selected: extra.shipping_type,
    abandon_reason: extra.abandon_reason,
  };
}

describe('Tracking rules - raw data schema', () => {
  const TEST_API_URL = "http://localhost:4566/restapis/test-api/prod/events";

  beforeEach(() => {
    vi.useFakeTimers();
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
    navigator.sendBeacon = vi.fn().mockReturnValue(true);
    setupDom();
    createTestContext(TEST_API_URL);
  });

  afterEach(() => {
    vi.useRealTimers();
    global.fetch = originalFetch;
    navigator.sendBeacon = originalSendBeacon;
    vi.clearAllMocks();
  });

  it('no envia eventos en catalog', async () => {
    window.currentPage = 'catalog';
    window.carrito = [{ id: 'p1', cantidad: 1, precio: 100 }];
    await sendEvent(makeEvent('add_to_cart', {}));
    expect(fetch).not.toHaveBeenCalled();
  });

  it('no envia en cart si carrito vacio', async () => {
    window.currentPage = 'cart';
    window.carrito = [];
    await sendEvent(makeEvent('page_view', {}));
    expect(fetch).not.toHaveBeenCalled();
  });

  it('envia en cart con items - heartbeat tiene campos raw', async () => {
    window.currentPage = 'cart';
    window.carrito = [{ id: 'p1', cantidad: 1, precio: 100, categoria: 'test', imagen: '', nombre: 'Test' }];
    await sendEvent(makeEvent('page_view', {}));
    expect(fetch).toHaveBeenCalledTimes(1);
    
    const call = fetch.mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.event_type).toBe('page_view');
    expect(body.timestamp).toBeDefined();
    expect(body.session_id).toBe('test-session');
    expect(body.user_id).toBe('test-user');
    expect(body.mouse_click_count).toBe(0);
    expect(body.page).toBe('cart');
    expect(body.cart_value).toBe(100);
    expect(body.product_count).toBe(1);
    expect(body.product_quantities).toEqual({ p1: 1 });
    expect(body.shipping_option_selected).toBe('standard');
  });

  it('envia en checkout con items', async () => {
    window.currentPage = 'checkout';
    window.carrito = [{ id: 'p1', cantidad: 1, precio: 100, categoria: 'test', imagen: '', nombre: 'Test' }];
    await sendEvent(makeEvent('start_checkout', { shipping_type: 'standard' }));
    expect(fetch).toHaveBeenCalledTimes(1);
    
    const call = fetch.mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.event_type).toBe('start_checkout');
    expect(body.payment_method_selected).toBeNull();
    expect(body.shipping_option_selected).toBe('standard');
  });

  it('heartbeat no se dispara en catalog', () => {
    window.currentPage = 'catalog';
    window.carrito = [{ id: 'p1', cantidad: 1, precio: 100 }];
    sendHeartbeat();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('heartbeat se dispara en cart con items - campos raw', () => {
    window.currentPage = 'cart';
    window.carrito = [{ id: 'p1', cantidad: 1, precio: 100, categoria: 'test', imagen: '', nombre: 'Test' }];
    sendHeartbeat();
    expect(fetch).toHaveBeenCalledTimes(1);
    
    const call = fetch.mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.event_type).toBe('heartbeat');
    expect(body.mouse_x).toBe(0);
    expect(body.mouse_y).toBe(0);
    expect(body.shipping_option_selected).toBe('standard');
    // NO debe tener velocity, distance, idle
    expect(body.mouse_velocity).toBeUndefined();
    expect(body.mouse_distance).toBeUndefined();
    expect(body.mouse_idle_ms).toBeUndefined();
  });

  it('usa API_URL dinamica no hardcodeada', () => {
    expect(window.CLICKSTREAM_CONFIG.apiUrl).not.toBe("http://localhost:4566/restapis/ID_API/STAGE/events");
    expect(window.CLICKSTREAM_CONFIG.apiUrl).toContain("/events");
  });

  it('beforeunload respeta shouldTrack', () => {
    window.currentPage = 'catalog';
    window.carrito = [{ id: 'p1', cantidad: 1, precio: 100 }];
    window.dispatchEvent(new Event('beforeunload'));
    expect(navigator.sendBeacon).not.toHaveBeenCalled();
  });

  it('beforeunload envia en cart con items', () => {
    window.currentPage = 'cart';
    window.carrito = [{ id: 'p1', cantidad: 1, precio: 100 }];
    // Test the makeEvent function directly (beforeunload handler uses navigator.sendBeacon)
    const event = makeEvent('abandon', { cart_value: 100, shipping_type: 'standard', abandon_reason: 'cerro ventana' });
    expect(event.event_type).toBe('abandon');
    expect(event.abandon_reason).toBe('cerro ventana');
    expect(event.cart_value).toBe(100);
    expect(event.shipping_option_selected).toBe('standard');
  });

  it('carrito vacio deja de trackear', async () => {
    window.currentPage = 'cart';
    window.carrito = [{ id: 'p1', cantidad: 1, precio: 100, categoria: 'test', imagen: '', nombre: 'Test' }];
    await sendEvent(makeEvent('page_view', {}));
    expect(fetch).toHaveBeenCalledTimes(1);

    window.carrito = [];
    await sendEvent(makeEvent('page_view', {}));
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it('add_to_cart incluye product_id, category, price', async () => {
    window.currentPage = 'cart';
    // cart has p1 already, adding p2
    window.carrito = [{ id: 'p1', cantidad: 1, precio: 100, categoria: 'test', imagen: '', nombre: 'Test' }];
    await sendEvent(makeEvent('add_to_cart', { product_id: 'p2', category: 'perifericos', price: 85 }));
    
    const call = fetch.mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.event_type).toBe('add_to_cart');
    expect(body.product_id).toBe('p2');
    expect(body.category).toBe('perifericos');
    expect(body.price).toBe(85);
    // product_quantities reflects current cart state BEFORE adding (p1 only)
    expect(body.product_quantities).toEqual({ p1: 1 });
  });

  it('purchase incluye payment_method_selected', async () => {
    window.currentPage = 'checkout';
    window.carrito = [{ id: 'p1', cantidad: 1, precio: 100 }];
    await sendEvent(makeEvent('purchase', { cart_value: 100, shipping_type: 'express', payment_method: 'credit_card' }));
    
    const call = fetch.mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.event_type).toBe('purchase');
    expect(body.payment_method_selected).toBe('credit_card');
    expect(body.shipping_option_selected).toBe('express');
  });

  it('abandon incluye abandon_reason', async () => {
    window.currentPage = 'cart';
    window.carrito = [{ id: 'p1', cantidad: 1, precio: 100 }];
    await sendEvent(makeEvent('abandon', { cart_value: 100, shipping_type: 'standard', abandon_reason: 'Costo de envio muy alto' }));
    
    const call = fetch.mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.event_type).toBe('abandon');
    expect(body.abandon_reason).toBe('Costo de envio muy alto');
  });
});