// hamburger toggle
document.addEventListener('DOMContentLoaded' ,
    function(){
        const ham = document.getElementById('hamburger');
        const nav = document.getElementById('nav');
        if (ham){
            ham.addEventListener('click' , function(){
                if (nav.style.display === 'flex') {
                    nav.style.display = '' ;
                } else {
                    nav.style.display = 'flex' ;
                }
            });
        }
    }
);