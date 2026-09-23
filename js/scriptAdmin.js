// ============================================================
// КОНФИГУРАЦИЯ И ВСПОМОГАТЕЛЬНЫЕ УТИЛИТЫ
// ============================================================
// Константы маршрутов API для централизованного управления эндпоинтами
const API = {
  CATALOG: '/navigator/api/catalog',
  PERMANENT: '/navigator/api/permanent',
  IMAGES: '/navigator/api/images',
  ITEMS: '/navigator/api/items',
  PARSER: { START: '/navigator/api/parser/start', STATUS: '/navigator/api/parser/status' },
  IMPORT: '/navigator/api/import/json'
};
// Список URL-заглушек, которые сервер отдаёт для элементов без кастомной иконки
const PLACEHOLDERS = ['https://vm-ftp.anosov.ru/icons/folder.gif', 'http://vm-ftp.anosov.ru/icons/folder.gif', 'vm-ftp.anosov.ru/icons/folder.gif'];

// Глобальное состояние приложения. Хранит актуальные данные между вызовами функций
let catalogData = null, permanentItems = [], availableImages = [], selectedElement = null, selectedImage = null, filteredImages = [];

// Универсальная обёртка над fetch. Автоматически добавляет credentials:include,
// парсит JSON и выбрасывает понятные ошибки при статусах 4xx/5xx
async function apiFetch(url, opts = {}) {
  const res = await fetch(url, { credentials: 'include', ...opts });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Ошибка сервера: ${res.status}`);
  }
  return res.json();
}

// Проверяет, является ли переданный URL стандартной заглушкой системы
function isPlaceholderIcon(url) {
  return url && PLACEHOLDERS.some(p => url.includes(p));
}

// Выводит информационное сообщение в UI-блок #statusMessage с автоматическим скрытием через 5 секунд
function showStatus(msg, type = 'success') {
  const el = document.getElementById('statusMessage');
  if (!el) return;
  el.textContent = msg;
  el.className = `status-message status-${type}`;
  el.classList.remove('hidden');
  setTimeout(() => el.classList.add('hidden'), 5000);
}

// Отправляет системное браузерное уведомление. Запрашивает разрешение при первом вызове
function showBrowserNotification(title, body) {
  if (!('Notification' in window)) return;
  const push = () => new Notification(title, { body, icon: './page/logo.png', tag: 'parser-completed' });
  if (Notification.permission === 'granted') return push();
  if (Notification.permission !== 'denied') Notification.requestPermission().then(p => p === 'granted' && push());
}

// ============================================================
// ЗАГРУЗКА ДАННЫХ С СЕРВЕРА
// ============================================================
// Загружает структуру каталога, после чего перерисовывает дерево, списки родителей и импорт-списки
async function loadCatalog() { 
  catalogData = await apiFetch(API.CATALOG); 
  renderCatalogTree(); renderParentList(); renderImportParentList(); 
}
// Загружает список элементов, помеченных как "постоянные" (не удаляются парсером)
async function loadPermanentItems() { 
  const d = await apiFetch(API.PERMANENT); 
  permanentItems = d.permanent_items || []; 
}
// Загружает доступные изображения, сбрасывает фильтр и обновляет сетки/селекты
async function loadImages() { 
  availableImages = await apiFetch(API.IMAGES); 
  filteredImages = [...availableImages]; 
  populateImageSelects(); renderImagesGrids(); 
}

// ============================================================
// ДЕРЕВО КАТАЛОГА И ЛОГИКА ВЫБОРА
// ============================================================
// Рекурсивно строит DOM-дерево из JSON-структуры каталога.
// isRoot = true только при первом вызове, чтобы очистить контейнер
function renderCatalogTree(items = catalogData?.children, parentPath = '', container = document.getElementById('catalogTree'), isRoot = true) {
  if (isRoot) container.innerHTML = '';
  if (!items) return;
  
  for (const item of items) {
    const curPath = parentPath ? `${parentPath}/${item.name}` : item.name;
    const isPerm = permanentItems.includes(curPath);
    const hasKids = item.children?.length > 0;
    // Если элемент не папка и имеет валидную иконку, помечаем как FILE, иначе DIR
    const iconText = (!hasKids && item.icon && !isPlaceholderIcon(item.icon)) ? '📄' : '📁';
    
    const div = document.createElement('div');
    div.className = `tree-item${isPerm ? ' permanent' : ''}`;
    div.dataset.path = curPath;
    div.innerHTML = `
      <span class="tree-toggle${hasKids ? ' expanded' : ''}" style="${hasKids ? '' : 'visibility:hidden'}"></span>
      <span>${iconText}</span>
      <span>${item.name.toUpperCase()}</span>
    `;
    // Делегирование клика: если нажато на стрелку - сворачиваем/разворачиваем, иначе - выбираем элемент
    div.onclick = (e) => e.target.classList.contains('tree-toggle') ? toggleTreeChildren(div, curPath) : selectTreeItem(div, curPath, item);
    
    container.appendChild(div);
    if (hasKids) {
      const kidsDiv = document.createElement('div');
      kidsDiv.className = 'tree-children';
      kidsDiv.dataset.parentPath = curPath;
      renderCatalogTree(item.children, curPath, kidsDiv, false);
      container.appendChild(kidsDiv);
    }
  }
}

// Переключает видимость дочерних элементов и обновляет CSS-класс стрелки
function toggleTreeChildren(el, path) {
  const kids = document.querySelector(`.tree-children[data-parent-path="${path}"]`);
  const tog = el.querySelector('.tree-toggle');
  if (!kids) return;
  const isHidden = kids.classList.toggle('hidden');
  tog.classList.toggle('collapsed', isHidden);
  tog.classList.toggle('expanded', !isHidden);
}

// Обновляет текстовую иконку элемента в дереве (DIR/FILE) на основе нового URL
function updateTreeIcon(path, iconUrl) {
  const el = document.querySelector(`.tree-item[data-path="${path}"]`);
  if (el?.querySelector('span:nth-child(2)')) {
    el.querySelector('span:nth-child(2)').textContent = (!isPlaceholderIcon(iconUrl) && iconUrl?.trim()) ? '📄' : '📁';
  }
}

// Обработчик выбора элемента: снимает выделение со всех, заполняет форму редактирования,
// синхронизирует глобальное состояние и подсвечивает текущую иконку в сетке
function selectTreeItem(el, path, item) {
  document.querySelectorAll('.tree-item').forEach(e => e.classList.remove('selected'));
  el.classList.add('selected');
  selectedElement = { path, ...item };
  selectedImage = item.icon || '';
  
  const form = document.getElementById('editForm');
  form.classList.remove('hidden');
  document.getElementById('editPath').value = path;
  document.getElementById('editName').value = item.name.toUpperCase();
  document.getElementById('editIcon').value = item.icon || '';
  document.getElementById('editUrl').value = item.url || '';
  document.getElementById('editPermanent').checked = permanentItems.includes(path);
  
  highlightSelectedImage(item.icon, 'editImagesGrid');
  updateTreeIcon(path, item.icon);
}

// ============================================================
// СЕТКА ИЗОБРАЖЕНИЙ И ВЫПАДАЮЩИЕ СПИСКИ
// ============================================================
// Заполняет селекты иконок опциями из загруженного массива изображений
function populateImageSelects() {
  const opts = availableImages.map(i => `<option value="${i.path}">${i.name}</option>`).join('');
  document.querySelectorAll('#editIcon, #addIcon').forEach(sel => sel.innerHTML = `<option value="">-- Выберите иконку --</option>${opts}`);
}

function renderImagesGrids() { renderImageGrid('editImagesGrid', 'editIcon'); renderImageGrid('addImagesGrid', 'addIcon'); }

// Рендерит сетку превью изображений. Использует ленивую загрузку (loading="lazy").
// При клике обновляет соответствующий селект, глобальную переменную selectedImage и иконку в дереве
function renderImageGrid(containerId, selectId, images = availableImages) {
  const cont = document.getElementById(containerId);
  if (!cont) return;
  cont.innerHTML = images.map(img => {
    const src = img.path.startsWith('http') ? img.path : `/${img.path}`;
    return `<div class="image-item" data-src="${src}"><img src="${src}" alt="${img.name}" loading="lazy" onerror="this.style.display='none'"></div>`;
  }).join('');
  
  cont.onclick = (e) => {
    const item = e.target.closest('.image-item');
    if (!item) return;
    cont.querySelectorAll('.image-item').forEach(el => el.classList.remove('selected'));
    item.classList.add('selected');
    const src = item.dataset.src;
    document.getElementById(selectId).value = src;
    selectedImage = src;
    if (selectId === 'editIcon' && selectedElement) updateTreeIcon(selectedElement.path, src);
  };
}

// Находит и подсвечивает элемент в сетке, соответствующий переданному URL иконки
function highlightSelectedImage(icon, gridId) {
  document.querySelectorAll(`#${gridId} .image-item`).forEach(el => {
    const img = el.querySelector('img');
    el.classList.toggle('selected', img && img.src === icon);
  });
}

// ============================================================
// СПИСКИ РОДИТЕЛЬСКИХ ПАПОК И ПОИСК
// ============================================================
// Фабричная функция для создания элемента выбора родительской папки. 
// Вынесена отдельно, чтобы избежать дублирования кода для двух разных списков
function createParentItem(path, label, container, onSelect) {
  const div = document.createElement('div');
  div.className = 'parent-item'; div.dataset.path = path;
  div.innerHTML = `<span>DIR</span><span>${label}</span>`;
  div.onclick = () => onSelect(div, path);
  container.appendChild(div);
}

// Рекурсивно обходит дерево каталога и добавляет только папки (где children не null)
function renderParentListRecursive(items, path, container, onSelect) {
  for (const it of (items || [])) {
    const cur = path ? `${path}/${it.name}` : it.name;
    if (it.children !== null) {
      createParentItem(cur, cur, container, onSelect);
      if (it.children?.length) renderParentListRecursive(it.children, cur, container, onSelect);
    }
  }
}

// Инициализирует список родителей для формы добавления
function renderParentList() {
  const c = document.getElementById('parentList'); if (!c) return; c.innerHTML = '';
  createParentItem('', 'Корневая папка', c, (el, p) => selectParent(el, p));
  renderParentListRecursive(catalogData?.children, '', c, (el, p) => selectParent(el, p));
}
function selectParent(el, path) {
  document.querySelectorAll('.parent-item').forEach(e => e.classList.remove('selected'));
  el.classList.add('selected');
  document.getElementById('addParentPath').value = path;
}

// Инициализирует список родителей для формы импорта JSON
function renderImportParentList() {
  const c = document.getElementById('importParentList'); if (!c) return; c.innerHTML = '';
  createParentItem('', 'Корневая папка', c, (el, p) => selectImportParent(el, p));
  renderParentListRecursive(catalogData?.children, '', c, (el, p) => selectImportParent(el, p));
}
function selectImportParent(el, path) {
  document.querySelectorAll('#importParentList .parent-item').forEach(e => e.classList.remove('selected'));
  el.classList.add('selected');
  document.getElementById('importParentPath').value = path;
}

// Навешивает обработчики ввода на все поля поиска. Фильтрация происходит в реальном времени
function setupSearch() {
  document.getElementById('treeSearch').oninput = (e) => searchInTree(e.target.value);
  document.getElementById('imageSearch').oninput = (e) => {
    const q = e.target.value.toLowerCase().trim();
    filteredImages = availableImages.filter(img => img.name.toLowerCase().includes(q));
    renderImageGrid('addImagesGrid', 'addIcon', filteredImages);
  };
  document.getElementById('parentSearch').oninput = (e) => filterParentList(e.target.value.toLowerCase().trim());
  const impSearch = document.getElementById('importParentSearch');
  if (impSearch) impSearch.oninput = (e) => filterImportParentList(e.target.value.toLowerCase().trim());
}
function searchInTree(q) { applyFilter('#catalogTree .tree-item', q); }
function filterParentList(q) { applyFilter('#parentList .parent-item', q); }
function filterImportParentList(q) { applyFilter('#importParentList .parent-item', q); }
// Универсальный фильтр: скрывает элементы, чей последний span не содержит поисковый запрос
function applyFilter(selector, q) {
  document.querySelectorAll(selector).forEach(el => {
    const txt = el.querySelector('span:last-child')?.textContent.toLowerCase() || '';
    el.style.display = (!q || txt.includes(q)) ? 'flex' : 'none';
  });
}

// ============================================================
// ФОРМЫ И CRUD ОПЕРАЦИИ
// ============================================================
// Извлекает итоговый URL иконки, приоритизируя выбранный в сетке, затем селект, затем дефолт.
// Автоматически очищает заглушки до пустой строки
function getCleanIcon(inputId) {
  const val = selectedImage || document.getElementById(inputId).value || 'folder.png';
  return isPlaceholderIcon(val) ? '' : val;
}

// Отправка PUT-запроса на обновление элемента. Синхронизирует permanent-флаг и уведомляет другие вкладки
async function updateItem() {
  const path = document.getElementById('editPath').value;
  const updates = { name: document.getElementById('editName').value.toUpperCase(), icon: getCleanIcon('editIcon') };
  const url = document.getElementById('editUrl').value;
  if (url) updates.url = url;
  try {
    await apiFetch(API.ITEMS, { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ path, updates }) });
    await togglePermanent(path, document.getElementById('editPermanent').checked);
    showStatus('Элемент обновлён'); selectedImage = null; await loadCatalog(); await loadPermanentItems();
    localStorage.setItem('catalogUpdated', Date.now());
  } catch (e) { showStatus('Ошибка обновления: ' + e.message, 'error'); }
}

// Отправка POST-запроса на создание элемента. При необходимости сразу ставит permanent-флаг
async function addItem() {
  const parentPath = document.getElementById('addParentPath').value;
  const name = document.getElementById('addName').value.toUpperCase();
  const body = { parent_path: parentPath, name, icon: getCleanIcon('addIcon') };
  const url = document.getElementById('addUrl').value;
  if (url) body.url = url;
  try {
    await apiFetch(API.ITEMS, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) });
    if (document.getElementById('addPermanent').checked) await togglePermanent(parentPath ? `${parentPath}/${name}` : name, true);
    showStatus('Элемент добавлен'); document.getElementById('addForm').reset(); document.getElementById('addParentPath').value = ''; selectedImage = null;
    await loadCatalog(); await loadPermanentItems(); localStorage.setItem('catalogUpdated', Date.now());
  } catch (e) { showStatus('Ошибка добавления: ' + e.message, 'error'); }
}

// Отправка DELETE-запроса. Перед удалением запрашивает подтверждение пользователя
async function deleteCurrentItem() {
  if (!selectedElement) return;
  if (!confirm(`Удалить "${selectedElement.name}"?`)) return;
  try {
    await apiFetch(API.ITEMS, { method: 'DELETE', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ path: selectedElement.path }) });
    await togglePermanent(selectedElement.path, false);
    showStatus('Элемент удалён'); document.getElementById('editForm').classList.add('hidden'); selectedElement = null; selectedImage = null;
    await loadCatalog(); await loadPermanentItems();
  } catch (e) { showStatus('Ошибка удаления: ' + e.message, 'error'); }
}

// Переключает статус "постоянный элемент" на сервере
async function togglePermanent(path, make) {
  await fetch(API.PERMANENT, { method: make ? 'POST' : 'DELETE', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({path}), credentials: 'include' }).catch(console.error);
}

// ============================================================
// ПАРСЕР, ЛОГИРОВАНИЕ И ПОЛЛИНГ СТАТУСА
// ============================================================
// Разблокирует все кнопки запуска парсера и возвращает исходный текст
function resetParserButtons() {
  document.querySelectorAll('button[onclick="startParser()"]').forEach(b => { b.disabled = false; b.textContent = 'Парсер'; });
}

// Форматирует и выводит логи в консоль браузера с группировкой по типам (error/info/log).
// Поддерживает как строковый, так и объектный формат логов
function logParser(logs) {
  if (!logs?.length) return;
  console.groupCollapsed(`[PARSER LOGS] ${new Date().toLocaleTimeString()}`);
  logs.forEach((l, i) => {
    const isObj = typeof l === 'object' && l !== null;
    const msg = isObj ? `[${l.timestamp || 'N/A'}] ${l.message}` : String(l);
    const type = isObj ? (l.type || 'log') : (/ERROR|Ошибк|WARNING/.test(msg) ? 'error' : /Успешно/.test(msg) ? 'info' : 'log');
    console[type === 'error' ? 'error' : type === 'info' ? 'info' : 'log'](`[${i}] ${msg}`);
    if (isObj && l.error_details) { console.groupCollapsed(`Детали ошибки #${i}`); console.dir(l.error_details); console.groupEnd(); }
  });
  console.groupEnd();
}

// Обновляет UI-блок статуса парсера. Если процесс активен, запускает рекурсивную проверку через 2 секунды
function updateParserUI(status) {
  const div = document.getElementById('parserStatus'), txt = document.getElementById('parserStatusText'), last = document.getElementById('parserLastRun');
  if (div && txt && last) {
    txt.textContent = status.message; last.textContent = status.last_run || '-';
    div.className = 'parser-status ' + (status.running ? 'running' : 'completed');
    logParser(status.logs);
  }
  if (status.running) setTimeout(checkParserStatus, 2000);
  else resetParserButtons();
}

// Запускает парсер на сервере. Блокирует интерфейс на время ожидания ответа
async function startParser() {
  document.querySelectorAll('button[onclick="startParser()"]').forEach(b => { b.disabled = true; b.textContent = 'Парсинг...'; });
  try { await apiFetch(API.PARSER.START, { method: 'POST' }); checkParserStatus(); }
  catch (e) { showStatus('Ошибка запуска: ' + e.message, 'error'); resetParserButtons(); }
}

// Опрос статуса парсера. При завершении делает все элементы постоянными, обновляет кэш и показывает уведомления
async function checkParserStatus() {
  try {
    const status = await apiFetch(API.PARSER.STATUS);
    updateParserUI(status);
    if (!status.running) {
      await makeAllItemsPermanent();
      await Promise.all([loadCatalog(), loadPermanentItems(), loadImages()]);
      showStatus('Парсинг завершён! Все элементы сохранены.');
      localStorage.setItem('catalogUpdated', Date.now());
      showBrowserNotification('Парсер завершил работу', 'Все элементы сохранены.');
    }
  } catch (e) { console.error(e); resetParserButtons(); }
}

// Рекурсивно собирает полные пути всех элементов в каталоге
async function getAllPaths(items = catalogData?.children, path = '') {
  let paths = [];
  for (const it of (items || [])) {
    const cur = path ? `${path}/${it.name}` : it.name;
    paths.push(cur);
    if (it.children?.length) paths.push(...getAllPaths(it.children, cur));
  }
  return paths;
}
// После парсинга помечает все новые элементы как permanent, чтобы они не удалялись при следующем запуске
async function makeAllItemsPermanent() {
  const all = await getAllPaths((await apiFetch(API.CATALOG)).children);
  for (const p of all) if (!permanentItems.includes(p)) await togglePermanent(p, true);
  await loadPermanentItems();
}

// ============================================================
// ИМПОРТ/ЭКСПОРТ ДАННЫХ И НАВИГАЦИЯ ПО ИНТЕРФЕЙСУ
// ============================================================
// Парсит JSON из текстового поля, отправляет на сервер с указанием родительской папки
async function importJsonData() {
  const data = document.getElementById('importJsonData').value.trim();
  if (!data) return showStatus('Введите JSON', 'error');
  try {
    const res = await apiFetch(API.IMPORT, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ json_data: data, parent_path: document.getElementById('importParentPath').value }) });
    showStatus(res.message || 'JSON импортирован');
    document.getElementById('importJsonData').value = ''; document.getElementById('importParentPath').value = '';
    await loadCatalog(); await loadPermanentItems();
  } catch (e) { showStatus('Ошибка импорта: ' + e.message, 'error'); }
}

// Выгружает плоский список всех элементов каталога в JSON-файл для скачивания
function exportJson() {
  fetch(API.CATALOG).then(r => r.json()).then(data => {
    const collect = (items, cat) => {
      let res = [];
      for (const it of (items || [])) {
        if (!it) continue;
        res.push({ name: it.name, icon: it.icon, url: it.url || null, modified: it.modified, catalog: cat });
        if (it.children?.length) res.push(...collect(it.children, it.name));
      }
      return res;
    };
    const all = [];
    for (const cat of (data.children || [])) all.push(...collect(cat.children, cat.name || 'Без названия'));
    const blob = new Blob([JSON.stringify(all, null, 2)], { type: 'application/json' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
    a.download = `catalog_export_${new Date().toISOString().slice(0,10)}.json`;
    a.click(); URL.revokeObjectURL(a.href);
    showStatus('JSON выгружен');
  }).catch(e => showStatus('Ошибка выгрузки: ' + e.message, 'error'));
}

// Переключает активные вкладки интерфейса, скрывая неактивные и показывая целевой контент
function setupTabs() {
  document.querySelectorAll('.tab').forEach(tab => tab.onclick = () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(`${tab.dataset.tab}Tab`).classList.add('active');
  });
}

// Привязывает submit-обработчики к формам с предотвращением стандартной отправки страницы
function setupForms() {
  document.getElementById('editForm').onsubmit = async (e) => { e.preventDefault(); await updateItem(); };
  document.getElementById('addForm').onsubmit = async (e) => { e.preventDefault(); await addItem(); };
}

// ============================================================
// ИНИЦИАЛИЗАЦИЯ И СИНХРОНИЗАЦИЯ МЕЖДУ ВКЛАДКАМИ
// ============================================================
document.addEventListener('DOMContentLoaded', async () => {
  // Параллельная загрузка всех зависимых данных для ускорения старта
  await Promise.all([loadCatalog(), loadPermanentItems(), loadImages(), apiFetch(API.PARSER.STATUS).then(updateParserUI)]);
  setupTabs(); setupForms(); setupSearch();
  renderParentList(); renderImportParentList();
  
  // Слушает события localStorage. Когда парсер в другой вкладке завершает работу,
  // текущая вкладка автоматически обновляет дерево, картинки и списки
  window.addEventListener('storage', (e) => {
    if (e.key === 'catalogUpdated') {
      Promise.all([loadCatalog(), loadImages(), loadPermanentItems()]);
      showStatus('Данные обновлены после завершения парсинга');
    }
  });
});

// Утилиты навигации для кнопок выхода и смены пароля
function logout() { window.location.href = '/navigator/logout'; }
function changePassword() { window.location.href = '/navigator/change-password'; }
