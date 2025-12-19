        const mobileMenuBtn = document.getElementById('mobileMenuBtn');
        const navLinks = document.getElementById('navLinks');
        
        mobileMenuBtn.addEventListener('click', () => {
            navLinks.classList.toggle('active');
            const icon = mobileMenuBtn.querySelector('i');
            if (icon.classList.contains('fa-bars')) {
                icon.classList.remove('fa-bars');
                icon.classList.add('fa-times');
            } else {
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        });
        
        document.querySelectorAll('.nav-links a').forEach(link => {
            link.addEventListener('click', () => {
                navLinks.classList.remove('active');
                const icon = mobileMenuBtn.querySelector('i');
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            });
        });
        
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                e.preventDefault();
                
                const targetId = this.getAttribute('href');
                if(targetId === '#') return;
                
                const targetElement = document.querySelector(targetId);
                if(targetElement) {
                    window.scrollTo({
                        top: targetElement.offsetTop - 80,
                        behavior: 'smooth'
                    });
                }
            });
        });

        const imagens1 = [
            'static/images/fibraDeVidro.jpg',
            'static/images/fibraDeVidro2.jpg',
            'static/images/fibraDeVidro3.jpg',
        ];  
        const imagens2 = [  
            'static/images/esmaltacao.jpg',
            'static/images/esmaltacao2.jpg',
            'static/images/esmaltacao3.jpg',
        ];
        const imagens3 = [
            'static/images/banho.jpg',
            'static/images/banho2.jpg',
            'static/images/banho3.jpg',
        ]
function iniciarSlide(idElemento, listaImagens, tempo) {
    let indice = 0;
    const elemento = document.getElementById(idElemento);
    if (!elemento) return;

    setInterval(() => {
        elemento.style.opacity = 0;

        setTimeout(() => {
            indice = (indice + 1) % listaImagens.length;
            elemento.src = listaImagens[indice];

            elemento.style.opacity = 1;
        }, 800);
        
    }, tempo);
}


iniciarSlide('card1', imagens1, 6000);
iniciarSlide('card2', imagens2, 6100);
iniciarSlide('card3', imagens3, 6200);