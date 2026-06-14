document.addEventListener('DOMContentLoaded', function () {
    /* ============================================================
     * 1. MENU MOBILE (drawer lateral)
     * ============================================================ */
    var mobileMenuBtn = document.getElementById('mobileMenuBtn');
    var navMenu = document.getElementById('navMenu');
    var navBackdrop = document.getElementById('navBackdrop');

    function abrirMenu() {
        navMenu.classList.add('active');
        if (navBackdrop) {
            navBackdrop.hidden = false;
            requestAnimationFrame(function () { navBackdrop.classList.add('active'); });
        }
        document.body.style.overflow = 'hidden';
        mobileMenuBtn.setAttribute('aria-expanded', 'true');
        var icon = mobileMenuBtn.querySelector('i');
        if (icon) { icon.classList.remove('fa-bars'); icon.classList.add('fa-times'); }
    }

    function fecharMenu() {
        navMenu.classList.remove('active');
        if (navBackdrop) {
            navBackdrop.classList.remove('active');
            setTimeout(function () { navBackdrop.hidden = true; }, 300);
        }
        document.body.style.overflow = '';
        mobileMenuBtn.setAttribute('aria-expanded', 'false');
        var icon = mobileMenuBtn.querySelector('i');
        if (icon) { icon.classList.remove('fa-times'); icon.classList.add('fa-bars'); }
    }

    if (mobileMenuBtn && navMenu) {
        mobileMenuBtn.addEventListener('click', function () {
            if (navMenu.classList.contains('active')) { fecharMenu(); } else { abrirMenu(); }
        });

        // Fecha ao clicar em qualquer link/botão do menu
        navMenu.querySelectorAll('a, button').forEach(function (el) {
            el.addEventListener('click', fecharMenu);
        });

        if (navBackdrop) { navBackdrop.addEventListener('click', fecharMenu); }

        // Fecha com ESC e ao voltar para o desktop
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && navMenu.classList.contains('active')) { fecharMenu(); }
        });
        window.addEventListener('resize', function () {
            if (window.innerWidth > 900 && navMenu.classList.contains('active')) { fecharMenu(); }
        });
    }

    /* ============================================================
     * 2. NAVBAR — sombra ao rolar
     * ============================================================ */
    var topNav = document.querySelector('.top-nav');
    if (topNav) {
        window.addEventListener('scroll', function () {
            topNav.classList.toggle('scrolled', window.scrollY > 30);
        });
    }

    /* ============================================================
     * 3. SCROLL SUAVE PARA ÂNCORAS
     * ============================================================ */
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
        anchor.addEventListener('click', function (e) {
            var targetId = this.getAttribute('href');
            if (targetId === '#') return;
            var targetElement = document.querySelector(targetId);
            if (targetElement) {
                e.preventDefault();
                window.scrollTo({ top: targetElement.offsetTop - 80, behavior: 'smooth' });
            }
        });
    });

    /* ============================================================
     * 4. ANIMAÇÃO AO ENTRAR NA VIEWPORT
     * ============================================================ */
    var observerTargets = document.querySelectorAll(
        '.service-card, .about-content, .info-item, .metric-card, .agendamento-card, .galeria-item, .teaser-item'
    );
    if ('IntersectionObserver' in window && observerTargets.length > 0) {
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

        observerTargets.forEach(function (el) {
            el.classList.add('animate-ready');
            observer.observe(el);
        });
    }

    /* ============================================================
     * 5. GALERIA — filtro por categoria
     * ============================================================ */
    var filtros = document.getElementById('galeriaFiltros');
    var grid = document.getElementById('galeriaGrid');
    var vazio = document.getElementById('galeriaVazio');

    if (filtros && grid) {
        var itens = Array.prototype.slice.call(grid.querySelectorAll('.galeria-item'));

        filtros.addEventListener('click', function (e) {
            var btn = e.target.closest('.filtro-chip');
            if (!btn) return;

            filtros.querySelectorAll('.filtro-chip').forEach(function (c) {
                c.classList.remove('ativo');
                c.setAttribute('aria-pressed', 'false');
            });
            btn.classList.add('ativo');
            btn.setAttribute('aria-pressed', 'true');

            var filtro = btn.getAttribute('data-filtro');
            var visiveis = 0;
            itens.forEach(function (item) {
                var ok = (filtro === 'todos' || item.getAttribute('data-categoria') === filtro);
                item.classList.toggle('escondido', !ok);
                if (ok) { visiveis++; }
            });
            if (vazio) { vazio.hidden = visiveis !== 0; }
        });
    }

    /* ============================================================
     * 6. LIGHTBOX
     * ============================================================ */
    var lightbox = document.getElementById('lightbox');
    if (lightbox && grid) {
        var lbImg = document.getElementById('lightboxImg');
        var lbLegenda = document.getElementById('lightboxLegenda');
        var lbFechar = document.getElementById('lightboxFechar');
        var lbPrev = document.getElementById('lightboxPrev');
        var lbNext = document.getElementById('lightboxNext');
        var indiceAtual = 0;

        function itensVisiveis() {
            return Array.prototype.slice.call(grid.querySelectorAll('.galeria-item:not(.escondido)'));
        }

        function mostrar(indice) {
            var lista = itensVisiveis();
            if (!lista.length) return;
            indiceAtual = (indice + lista.length) % lista.length;
            var item = lista[indiceAtual];
            var img = item.querySelector('img');
            lbImg.src = img.src;
            lbImg.alt = img.alt;
            var titulo = item.querySelector('.galeria-titulo');
            var cat = item.querySelector('.galeria-categoria');
            lbLegenda.textContent = (cat ? cat.textContent + ' — ' : '') + (titulo ? titulo.textContent : '');
        }

        function abrir(item) {
            var lista = itensVisiveis();
            mostrar(lista.indexOf(item));
            lightbox.classList.add('aberto');
            lightbox.setAttribute('aria-hidden', 'false');
            document.body.style.overflow = 'hidden';
        }

        function fechar() {
            lightbox.classList.remove('aberto');
            lightbox.setAttribute('aria-hidden', 'true');
            document.body.style.overflow = '';
        }

        grid.addEventListener('click', function (e) {
            var item = e.target.closest('.galeria-item');
            if (item) { abrir(item); }
        });
        grid.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                var item = e.target.closest('.galeria-item');
                if (item) { e.preventDefault(); abrir(item); }
            }
        });

        lbFechar.addEventListener('click', fechar);
        lbPrev.addEventListener('click', function () { mostrar(indiceAtual - 1); });
        lbNext.addEventListener('click', function () { mostrar(indiceAtual + 1); });
        lightbox.addEventListener('click', function (e) {
            if (e.target === lightbox) { fechar(); }
        });
        document.addEventListener('keydown', function (e) {
            if (!lightbox.classList.contains('aberto')) return;
            if (e.key === 'Escape') { fechar(); }
            if (e.key === 'ArrowLeft') { mostrar(indiceAtual - 1); }
            if (e.key === 'ArrowRight') { mostrar(indiceAtual + 1); }
        });
    }
});
