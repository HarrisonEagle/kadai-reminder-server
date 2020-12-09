var executed = false;
document.querySelectorAll('[aria-label="次の6か月間フィルタオプション"]')[0].click();
document.querySelectorAll('[data-limit="5"]')[0].click();
$("HTML").bind("DOMSubtreeModified", function() {
    var next = document.querySelectorAll('li[data-control="next"]')[1];
    next.click();
    var flag = next.className.includes('disabled')+""+$(".icon.fa.fa-circle-o-notch.fa-spin.fa-fw:visible").length;
    console.error(flag);
    if(flag=="true0"&&executed==false){
      executed = true;
      console.error("finished");
      return "finished";
    }
    console.log($(".w-100.event-name-container.text-truncate.line-height-3").length);
});