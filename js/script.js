/**
 * Навигатор по каталогу
 * Управление сайдбаром, поиск, история переходов и аудит действий
 */
document.addEventListener('DOMContentLoaded', () => {
    // ===== ЭЛЕМЕНТЫ ИНТЕРФЕЙСА =====
    
    const el = {
        sidebar: document.getElementById('sidebarLeft'),   
        overlay: document.querySelector('.overlay'),       
        openBtn: document.getElementById('openCatalog'),   
        closeBtn: document.getElementById('closeSidebar'), 
        backBtn: document.getElementById('backBtn'),       
        title: document.getElementById('catalogTitle'),    
        grid: document.getElementById('catalogGrid'),      
        searchInput: document.getElementById('searchInput'),   
        searchClearBtn: document.getElementById('searchClearBtn') 
    };

    // ===== СОСТОЯНИЕ ПРИЛОЖЕНИЯ =====
    
    let state = {
        history: [],      
        catalog: null,    
        searchQuery: ''   
    };

    // ===== АУДИТ: ОТПРАВКА СОБЫТИЙ =====
    /**
     * Отправляет событие аудита на сервер для логирования действий пользователя
     * @param {string} type - Тип события (например, 'link_click', 'video_player_open')
     * @param {string} id - Идентификатор объекта (имя элемента)
     * @param {string} objType - Тип объекта (например, 'catalog_item_link')
     * @param {string} desc - Описание события
     * @param {Object} data - Дополнительные данные события
     */
    function logEvent(type, id, objType, desc, data = {}) {
        // Извлекаем status из additional_data если он там есть
        const status = data.status || null;
        
        fetch('/navigator/api/audit/logs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                event_type: type,
                object_id: id,
                object_type: objType,
                description: desc,
                status: status,
                additional_data: data
            })
        }).catch(err => console.warn('Аудит не отправлен:', err)); 
    }

    // ===== СОХРАНЕНИЕ/ВОССТАНОВЛЕНИЕ СОСТОЯНИЯ =====
    /**
     * Сохраняет текущее состояние навигации и сайдбара в sessionStorage
     * Это позволяет восстановить позицию пользователя после перезагрузки страницы
     */
    function saveState() {
        sessionStorage.setItem('catalogState', JSON.stringify({
            historyStack: state.history,           
            sidebarActive: el.sidebar.classList.contains('active') 
        }));
    }

    /**
     * Восстанавливает состояние из sessionStorage при загрузке страницы
     * Если пользователь закрыл браузер внутри папки — вернёт его туда же
     */
    function restoreState() {
        const saved = sessionStorage.getItem('catalogState');
        if (!saved) return; 

        try {
            const data = JSON.parse(saved);
            if (data.historyStack?.length > 0) {
                state.history = data.historyStack; 
                render();                          
                if (data.sidebarActive) showSidebar(); 
            }
        } catch (e) {
            console.warn('Не удалось восстановить состояние', e);
        }
    }

    // ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
    
    /**
     * Получает путь к иконке, заменяя заглушки на логотип
     * @param {string} iconName - Имя файла или URL иконки
     * @returns {string} - Корректный путь к изображению
     */
    function getIconPath(iconName) {
        
        const placeholders = [
            'https://vm-ftp.anosov.ru/icons/folder.gif ',
            'http://vm-ftp.anosov.ru/icons/folder.gif',
            'vm-ftp.anosov.ru/icons/folder.gif'
        ];

        if (!iconName?.trim()) return 'page/logo.png';           
        if (placeholders.some(p => iconName.includes(p))) return 'page/logo.png'; 
        if (iconName.startsWith('http://') || iconName.startsWith('https://')) return iconName; 
        return `page/${iconName}`;                               
    }

    /**
     * Рекурсивный поиск элементов по названию во всём дереве каталога
     * @param {string} query - Поисковый запрос
     * @param {Array} items - Массив элементов для поиска (по умолчанию - корневые элементы)
     * @returns {Array} - Найденные элементы с полным путём в свойстве searchPath
     */
   // Функция поиска по каталогу: возвращает массив узлов, имя которых содержит query
    function searchCatalog(query, items = state.catalog?.children || []) {
        // Если запрос пустой или состоит из пробелов — не ищем ничего
        if (!query?.trim()) return [];
        
        // Приводим поисковую строку к нижнему регистру и обрезаем пробелы один раз
        const searchQuery = query.toLowerCase().trim();
        
        // Рекурсивный обход дерева каталогов
        // nodeList - массив узлов на текущем уровне, currentPath - путь от корня до этих узлов
        function findMatchesInTree(nodeList, currentPath = []) {
            const results = []; // накапливаем найденные узлы
            
            for (const node of nodeList) {
                // Формируем путь к текущему узлу: старый путь + имя узла
                const newPath = [...currentPath, node.name];
                
                // Если имя узла (без учёта регистра) содержит искомую подстроку
                if (node.name.toLowerCase().includes(searchQuery)) {
                    // Добавляем узел в результат, дополняя его полем searchPath (склеенный путь через " / ")
                    results.push({
                        ...node,
                        searchPath: newPath.join(' / ')
                    });
                }
                
                // Если у узла есть дочерние элементы — рекурсивно ищем в них,
                // передавая обновлённый путь
                if (node.children?.length > 0) {
                    results.push(...findMatchesInTree(node.children, newPath));
                }
            }
            
            return results; // возвращаем все найденные узлы на текущей и вложенных ветках
        }
        
        // Запускаем рекурсию с корневыми элементами каталога
        return findMatchesInTree(items);
    }

    /**
     * Проверяет, является ли URL видеофайлом по расширению
     * @param {string} url - Ссылка для проверки
     * @returns {boolean} - true, если это видеофайл
     */
    function isVideoFile(url) {
        if (!url) return false;
        
        const cleanUrl = url.trim().replace(/(https?)\s*:/i, '$1:');
        try {
            
            return /\.(mp4|webm|ogg|mov|avi|mkv|flv|wmv|m4v)\s*$/i.test(
                decodeURIComponent(cleanUrl)
            );
        } catch {
            return false; 
        }
    }

    // ===== ОТРИСОВКА ИНТЕРФЕЙСА =====
    
    /**
     * Отрисовывает текущий уровень каталога или результаты поиска
     */
    function render() {
        if (state.history.length === 0) return;

        const current = state.history[state.history.length - 1];
        
        const isSearchMode = !!state.searchQuery;
        
        const itemsToShow = isSearchMode ? searchCatalog(state.searchQuery) : current.items;
        
        el.title.textContent = isSearchMode 
            ? `Поиск: "${state.searchQuery}"` 
            : current.title;
        
        renderItems(itemsToShow, isSearchMode);
        
        el.backBtn.hidden = state.history.length <= 1;
        
        saveState();
    }

    /**
     * Рендерит список элементов в сетке каталога
     * @param {Array} items - Массив элементов для отображения
     * @param {boolean} isSearch - true, если это результаты поиска
     */
    function renderItems(items, isSearch) {
        el.grid.innerHTML = '';

        if (items.length === 0) {
            
            const empty = document.createElement('div');
            empty.className = 'item';
            empty.style.cssText = 'justify-content:center;align-items:center;color:#999;font-size:16px';
            empty.textContent = isSearch ? 'Ничего не найдено' : 'Пусто';
            el.grid.appendChild(empty);
            return;
        }

        items.forEach(item => el.grid.appendChild(createItemElement(item, isSearch)));
    }

    /**
     * Создаёт DOM-элемент (карточку) для одного элемента каталога
     * 
     * @param {Object} item - Данные элемента:
     *   - name {string} - Имя элемента
     *   - icon {string} - Путь к иконке или URL
     *   - children {Array} - Дочерние элементы (если это папка)
     *   - url {string} - Ссылка (если это файл или внешний ресурс)
     *   - searchPath {string} - Полный путь (добавляется при поиске)
     * @param {boolean} isSearch - true, если это результат поиска
     * @returns {HTMLElement} - Готовый div-элемент с иконкой, названием и путём (для поиска)
     */
    function createItemElement(item, isSearch) {
        const div = document.createElement('div');
        div.className = 'item';
        div.setAttribute('role', 'button');  
        div.setAttribute('tabindex', '0');   
        div.dataset.name = item.name;

        
        const img = document.createElement('img');
        img.className = 'item-icon';
        img.src = getIconPath(item.icon);
        img.alt = item.name;
        img.loading = 'lazy';                
        img.onerror = () => { img.src = 'page/logo.png'; }; 

        
        const nameSpan = document.createElement('span');
        nameSpan.className = 'item-name';
        nameSpan.textContent = item.name;

        
        const hasChildren = item.children?.length > 0;
        const isEmpty = !hasChildren && !item.url;
        
        if (isEmpty) {
            
            const msg = document.createElement('span');
            msg.className = 'item-empty-message';
            msg.textContent = '(пустой)';
            msg.style.cssText = 'color:#999;font-size:12px;margin-top:4px';
            nameSpan.append(document.createElement('br'), msg);
            div.style.opacity = '0.7'; 
        }

        
        
        if (isSearch && item.searchPath) {
            const pathSpan = document.createElement('span');
            pathSpan.className = 'item-search-path';
            pathSpan.textContent = item.searchPath;
            nameSpan.append(document.createElement('br'), pathSpan);
        }

        div.append(img, nameSpan);
        div._itemData = item; 
        return div;
    }

    // ===== НАВИГАЦИЯ =====

    /**
     * Сброс к корневому уровню каталога
     * Инициализирует историю первым элементом (корневая папка)
     */
    function resetToRoot() {
        if (!state.catalog) {
            // Если каталог ещё не загружен — ждём 100мс и пробуем снова
            setTimeout(resetToRoot, 100);
            return;
        }
        state.history = [{
            title: state.catalog.name,      
            items: state.catalog.children   
        }];
        render();
    }

    /**
     * Обработка клика по элементу каталога
     * @param {Event} e - Событие клика
     */
    function handleItemClick(e) {
        const itemDiv = e.target.closest('.item');
        if (!itemDiv?._itemData) return; 

        const item = itemDiv._itemData;
        const hasChildren = item.children?.length > 0;
        const isEmpty = !hasChildren && !item.url;

        if (isEmpty) {
            
            alert(`Элемент "${item.name}" пустой.`);
            return;
        }

        if (hasChildren) {
            
            if (state.searchQuery) clearSearch(); 
            state.history.push({ title: item.name, items: item.children }); 
            render();
        }  else if (item.url?.trim()) {
            
            saveState();
            const url = item.url.trim().replace(/(https?|ftp)\s*:/gi, '$1:'); 
            
            // Логируем клик по ссылке
            logEvent('link_click', item.name, 'catalog_item_link', 
                `Переход по ссылке: ${item.name}`, { url, status: 'initiated' });

            // Всегда открываем ссылку напрямую в новой вкладке (или скачиваем, если браузер так настроен)
            try {
                const a = document.createElement('a');
                a.href = url;
                a.target = '_blank';
                a.rel = 'noopener noreferrer'; 
                document.body.append(a);
                a.click();
                a.remove();
                
                logEvent('external_link_open', item.name, 'external_link', 
                    `Внешняя ссылка: ${item.name}`, { url, status: 'success' });
            } catch (err) {
                
                logEvent('external_link_error', item.name, 'external_link', 
                    `Ошибка ссылки: ${item.name}`, { url, error: err.message });
            }

            if (state.searchQuery) clearSearch(); 
        }
    }

    /**
     * Кнопка "Назад" — возврат на уровень выше
     * Если активен поиск — сбрасывает его вместо возврата
     */
    function goBack() {
        if (state.history.length > 1) {
            state.history.pop(); 
            render();
        } else if (state.searchQuery) {
            clearSearch(); 
        }
    }

    /**
     * Очистка поиска и возврат к корневой папке
     * 
     * Вызывается при:
     * - Кликe на кнопку очистки (крестик в поле поиска)
     * - Нажатии Escape при активном поиске
     * - Переходе в папку из результатов поиска
     */
    function clearSearch() {
        
        state.searchQuery = '';
        
        el.searchInput.value = '';
        
        el.searchClearBtn.hidden = true;
        
        resetToRoot();
    }

    // ===== САЙДБАР =====

    /**
     * Показать сайдбар с каталогом
     * Если данные ещё не загружены — сначала загружает их
     */
    function showSidebar() {
        if (!state.catalog) {
            loadCatalog().then(showSidebar); // Ждём загрузки, затем показываем
            return;
        }
        if (el.sidebar.classList.contains('active')) return; 

        resetToRoot();                
        el.sidebar.removeAttribute('hidden');
        el.overlay.removeAttribute('hidden');
        void el.sidebar.offsetHeight; 
        el.sidebar.classList.add('active');
        el.overlay.classList.add('active');
        el.openBtn.setAttribute('aria-expanded', 'true');
        saveState();
    }

    /**
     * Скрыть сайдбар с анимацией
     * Ждёт завершения CSS-перехода перед полным скрытием
     */
    function hideSidebar() {
        if (!el.sidebar.classList.contains('active')) return; 

        el.sidebar.classList.remove('active');
        el.overlay.classList.remove('active');
        el.openBtn.setAttribute('aria-expanded', 'false');

        let done = false;
        const onEnd = () => {
            if (done) return;
            done = true;
            el.sidebar.setAttribute('hidden', '');
            el.overlay.setAttribute('hidden', '');
            clearTimeout(timer);
            saveState();
        };

        
        const timer = setTimeout(onEnd, 1500);
        el.sidebar.addEventListener('transitionend', onEnd);
        el.overlay.addEventListener('transitionend', onEnd);
    }

    // ===== ЗАГРУЗКА ДАННЫХ =====

    /**
     * Загружает дерево каталога с сервера через API
     * @returns {Promise<Object|null>} - Данные каталога или null при ошибке
     */
    async function loadCatalog() {
        try {
            const res = await fetch('/navigator/api/catalog');
            if (!res.ok) throw new Error('Ошибка загрузки');
            state.catalog = await res.json();
            
            if (el.sidebar.classList.contains('active')) resetToRoot();
            return state.catalog;
        } catch (e) {
            console.error('Не удалось загрузить каталог:', e);
            
            state.catalog = { name: 'Ошибка загрузки', children: [] };
        }
    }

    /**
     * Обновляет каталог из сервера и перерисовывает текущий вид
     * Вызывается при внешних изменениях (например, из других вкладок)
     */
    function refreshCatalog() {
        loadCatalog().then(() => {
            if (state.history.length > 0) render();
        });
    }

    // ===== ОБРАБОТЧИКИ СОБЫТИЙ =====

    
    el.openBtn.addEventListener('click', () => {
        logEvent('web_resource_view', 'main_page_catalog', 'ui_element', 'Открытие каталога');
        showSidebar();
    });

    
    el.closeBtn.addEventListener('click', hideSidebar);
    el.overlay.addEventListener('click', hideSidebar);
    
    
    el.backBtn.addEventListener('click', goBack);

    
    el.grid.addEventListener('click', e => {
        const itemDiv = e.target.closest('.item');
        if (itemDiv?._itemData) {
            const item = itemDiv._itemData;
            
            logEvent('web_resource_view', item.name, 'catalog_item', 
                `Просмотр: ${item.name}`, { hasChildren: item.children?.length > 0 });
        }
        handleItemClick(e);
    });

    
    el.grid.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') {
            const item = e.target.closest('.item');
            if (item) {
                e.preventDefault();
                handleItemClick({ target: item });
            }
        }
    });

    // ===== ОБРАБОТЧИКИ СОБЫТИЙ =====

    
    
    
    
    
    el.searchInput.addEventListener('input', e => {
        state.searchQuery = e.target.value.trim();
        el.searchClearBtn.hidden = state.searchQuery === '';
        render();
    });

    
    el.searchClearBtn.addEventListener('click', clearSearch);

    
    
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape' && el.sidebar.classList.contains('active')) {
            state.searchQuery ? clearSearch() : hideSidebar();
        }
    });

    
    (async () => {
        await loadCatalog();   
        restoreState();        
        
        
        window.addEventListener('storage', e => {
            if (e.key === 'catalogUpdated') refreshCatalog();
        });
    })();
})
