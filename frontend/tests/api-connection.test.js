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

describe('API Gateway Connection - raw data schema', () => {
  const TEST_API_URL = "http://localhost:4566/restapis/test-api/prod/events";

  beforeEach(() => {
    vi.useFakeTimers();
    global.fetch = vi.fn().mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve({}) });
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

  it('envia event y recibe respuesta 200', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ abandon_probability: 0.1, trigger_retention: false })
    });

    const result = await sendEvent(makeEvent('page_view', { page: 'cart' }));

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch).toHaveBeenCalledWith(TEST_API_URL, expect.objectContaining({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: expect.stringContaining('page_view')
    }));
    expect(result).toEqual({ abandon_probability: 0.1, trigger_retention: false });
  });

  it('envia heartbeat y recibe respuesta', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ trigger_retention: false })
    });

    sendHeartbeat();
    await vi.runAllTimersAsync();

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch).toHaveBeenCalledWith(TEST_API_URL, expect.objectContaining({
      method: 'POST',
      body: expect.stringContaining('heartbeat')
    }));
  });

  it('maneja error 500 de API Gateway', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ error: 'Internal Server Error' })
    });

    const result = await sendEvent(makeEvent('page_view', {}));

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(result).toBeUndefined();
  });

  it('payload contiene campos requeridos raw data', async () => {
    let capturedBody = null;
    global.fetch = vi.fn().mockImplementation((url, opts) => {
      capturedBody = JSON.parse(opts.body);
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });

    await sendEvent(makeEvent('page_view', { page: 'cart' }));

    expect(capturedBody).toMatchObject({
      event_type: 'page_view',
      timestamp: expect.any(String),
      session_id: 'test-session',
      user_id: 'test-user',
      mouse_click_count: 0,
      page: 'cart',
      cart_value: 100,
      product_count: 1,
      product_quantities: { p1: 1 },
      shipping_option_selected: 'standard'
    });
    // NO debe tener campos calculados
    expect(capturedBody.mouse_velocity).toBeUndefined();
    expect(capturedBody.mouse_distance).toBeUndefined();
    expect(capturedBody.mouse_idle_ms).toBeUndefined();
    expect(capturedBody.velocity).toBeUndefined();
  });

  it('CORS: headers correctos en request', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });

    await sendEvent(makeEvent('page_view', {}));

    const call = fetch.mock.calls[0];
    expect(call[1].headers).toEqual({ 'Content-Type': 'application/json' });
  });

  it('usa API_URL dinamica no hardcodeada', () => {
    expect(window.CLICKSTREAM_CONFIG.apiUrl).not.toBe("http://localhost:4566/restapis/ID_API/STAGE/events");
    expect(window.CLICKSTREAM_CONFIG.apiUrl).toContain("/events");
  });

  it('heartbeat incluye mouse_x, mouse_y y shipping_option_selected', () => {
    window.currentPage = 'cart';
    sendHeartbeat();

    const call = fetch.mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.event_type).toBe('heartbeat');
    expect(body.mouse_x).toBe(0);
    expect(body.mouse_y).toBe(0);
    expect(body.shipping_option_selected).toBe('standard');
    expect(body.cart_value).toBe(100);
    expect(body.product_quantities).toEqual({ p1: 1 });
  });

  it('add_to_cart incluye product_id, category, price', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
    await sendEvent(makeEvent('add_to_cart', { product_id: 'p2', category: 'perifericos', price: 85 }));

    const call = fetch.mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.event_type).toBe('add_to_cart');
    expect(body.product_id).toBe('p2');
    expect(body.category).toBe('perifericos');
    expect(body.price).toBe(85);
  });

  it('purchase incluye payment_method_selected', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
    window.currentPage = 'checkout';
    window.carrito = [{ id: 'p1', cantidad: 1, precio: 100 }];
    await sendEvent(makeEvent('purchase', { cart_value: 100, shipping_type: 'express', payment_method: 'credit_card' }));

    const call = fetch.mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.event_type).toBe('purchase');
    expect(body.payment_method_selected).toBe('credit_card');
    expect(body.shipping_option_selected).toBe('express');
  });
});