/* Noninteractive desktop enlargement; Inspect remains the touch alternative. */
function installCardHover(root){
    let timer,source,popup,shade;
    const fine=matchMedia('(hover:hover) and (pointer:fine)');
    function hide(){clearTimeout(timer);popup?.remove();popup=null;shade?.remove();shade=null;source=null;}
    function show(card){
        if(!card.isConnected||document.querySelector('dialog[open]'))return;
        shade=document.createElement('div');shade.className='card-inspection-shade';document.body.append(shade);
        popup=document.createElement('aside');popup.className='card-hover-preview';popup.setAttribute('role','tooltip');
        const copy=card.cloneNode(true);copy.classList.remove('tapped','target');copy.removeAttribute('data-action');copy.removeAttribute('tabindex');copy.removeAttribute('role');
        copy.querySelectorAll('button,select,input,.card-controls').forEach(x=>x.remove());popup.append(copy);document.body.append(popup);
        const rect=card.getBoundingClientRect(),width=popup.offsetWidth,height=popup.offsetHeight;
        const right=rect.right+12,left=right+width<=innerWidth-10?right:rect.left-width-12;
        popup.style.left=Math.max(10,Math.min(left,innerWidth-width-10))+'px';
        popup.style.top=Math.max(10,Math.min(rect.top,innerHeight-height-10))+'px';
    }
    root.addEventListener('pointerover',e=>{if(!fine.matches||e.pointerType==='touch')return;const card=e.target.closest('.card');if(!card||source===card)return;hide();source=card;timer=setTimeout(()=>show(card),350);});
    root.addEventListener('pointerout',e=>{if(source&&!source.contains(e.relatedTarget))hide();});
    root.addEventListener('pointerdown',hide);
    document.addEventListener('keydown',e=>{if(e.key==='Escape')hide();});
    window.addEventListener('scroll',hide,true);window.addEventListener('resize',hide);
    new MutationObserver(()=>{if(source&&!source.isConnected)hide();}).observe(root,{childList:true,subtree:true});
}
