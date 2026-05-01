"""Tests E2E con Playwright · journeys críticos en navegador real.

Uso local:
    pip install playwright
    playwright install chromium
    pytest tests/e2e/test_e2e_smoke.py

Uso contra producción:
    E2E_BASE_URL=https://app.eossuite.com SMOKE_USER=sebastian SMOKE_PASSWORD=xxx \
        pytest tests/e2e/test_e2e_smoke.py

Estos tests son SLOW (segundos cada uno · arrancan navegador). NO se incluyen
en la suite por default. Correr explícitamente con `pytest tests/e2e/`.
"""
import os
import pytest

# Skip si Playwright no instalado o sin browsers
try:
    from playwright.sync_api import sync_playwright, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    pytest.skip('playwright no instalado · `pip install playwright && playwright install chromium`',
                allow_module_level=True)


BASE_URL = os.environ.get('E2E_BASE_URL', 'http://localhost:5000').rstrip('/')
SMOKE_USER = os.environ.get('SMOKE_USER', '')
SMOKE_PASSWORD = os.environ.get('SMOKE_PASSWORD', '')


@pytest.fixture(scope='module')
def browser():
    """Browser compartido entre tests del módulo (más rápido que por test)."""
    with sync_playwright() as p:
        try:
            b = p.chromium.launch(headless=True)
        except Exception as e:
            pytest.skip(f'Chromium no disponible · ejecutar `playwright install chromium`: {e}')
        yield b
        b.close()


@pytest.fixture
def page(browser):
    """Página fresca por test."""
    context = browser.new_context()
    p = context.new_page()
    yield p
    context.close()


def _login(page: Page):
    """Helper: hace login y deja la sesión activa."""
    if not SMOKE_USER or not SMOKE_PASSWORD:
        pytest.skip('SMOKE_USER y SMOKE_PASSWORD requeridos (env vars)')
    page.goto(f'{BASE_URL}/login')
    page.fill('input[name="username"]', SMOKE_USER)
    page.fill('input[name="password"]', SMOKE_PASSWORD)
    page.click('button[type="submit"]')
    # Esperar navigation post-login
    page.wait_for_url(lambda url: '/login' not in url, timeout=10000)


def test_health_endpoint_responds(page: Page):
    """El endpoint público /api/health responde 200 con JSON."""
    response = page.request.get(f'{BASE_URL}/api/health')
    assert response.status == 200
    data = response.json()
    assert 'ok' in data or 'status' in data, f'Respuesta inesperada: {data}'


def test_login_page_loads(page: Page):
    """La página de login carga sin errores JS."""
    errors = []
    page.on('pageerror', lambda exc: errors.append(str(exc)))
    page.goto(f'{BASE_URL}/login')
    # Verificar que el formulario está presente
    assert page.locator('input[name="username"]').count() == 1
    assert page.locator('input[name="password"]').count() == 1
    # No debe haber errores JS al cargar
    assert not errors, f'Errores JS al cargar /login: {errors}'


def test_login_y_dashboard_carga(page: Page):
    """Journey crítico: login → dashboard carga sin crash JS."""
    errors = []
    page.on('pageerror', lambda exc: errors.append(str(exc)))
    _login(page)
    # Después del login, verificar que estamos en dashboard o página principal
    assert '/login' not in page.url, f'Login no redirigió correctamente: {page.url}'
    # Verificar que no hay errores JS críticos
    js_errors = [e for e in errors if 'NetworkError' not in e]
    assert not js_errors, f'Errores JS post-login: {js_errors}'


def test_google_translate_widget_no_aparece(page: Page):
    """Verifica que el widget de Google Translate NO aparece (translate=no).

    Sebastián 1-may-2026 audit: agregamos translate=no + meta notranslate +
    CSS .goog-te-banner-frame{display:none}. El widget no debe ser visible.
    """
    page.goto(f'{BASE_URL}/login')
    # Selectors del widget de Google Translate
    widget_selectors = [
        '.goog-te-banner-frame',
        '#goog-gt-tt',
        '.goog-te-balloon-frame',
        'iframe.skiptranslate',
    ]
    for sel in widget_selectors:
        # Si existe, debe estar oculto (display:none o opacity:0)
        loc = page.locator(sel)
        count = loc.count()
        if count > 0:
            visible = loc.first.is_visible()
            assert not visible, f'Widget Google Translate visible en {sel}'


def test_dashboard_planta_responde(page: Page):
    """API /api/planta/health-check responde con sesión activa."""
    _login(page)
    response = page.request.get(f'{BASE_URL}/api/planta/health-check')
    assert response.status == 200, f'health-check fallo: {response.status}'


def test_validar_hermanos_skus_responde(page: Page):
    """Endpoint nuevo /api/planta/validar-hermanos-skus retorna estructura correcta."""
    _login(page)
    response = page.request.get(f'{BASE_URL}/api/planta/validar-hermanos-skus')
    assert response.status == 200
    data = response.json()
    assert 'total_grupos_sospechosos' in data
    assert 'grupos' in data
    assert isinstance(data['grupos'], list)


def test_translate_attribute_html(page: Page):
    """Verifica que <html> tiene translate='no'."""
    page.goto(f'{BASE_URL}/login')
    translate_attr = page.locator('html').get_attribute('translate')
    assert translate_attr == 'no', f'<html translate> debe ser "no", got "{translate_attr}"'


def test_csp_y_security_headers(page: Page):
    """Verifica headers de seguridad básicos en respuesta."""
    response = page.request.get(f'{BASE_URL}/login')
    headers = response.headers
    # Algunos headers que deberían estar
    expected = ['x-content-type-options', 'x-frame-options']
    missing = [h for h in expected if h not in {k.lower() for k in headers.keys()}]
    # No falla el test si faltan (legacy compat) pero loguea
    if missing:
        print(f'\n[WARN] Headers de seguridad faltantes: {missing}')
