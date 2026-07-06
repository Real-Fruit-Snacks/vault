(function () {
  "use strict";
  var blocks = document.querySelectorAll(".base-block");
  Array.prototype.forEach.call(blocks, function (block) {
    var tabs = block.querySelectorAll(".base-tab");
    if (!tabs.length) return;
    Array.prototype.forEach.call(tabs, function (tab) {
      tab.addEventListener("click", function () {
        var name = tab.getAttribute("data-view");
        Array.prototype.forEach.call(tabs, function (t) {
          t.classList.toggle("active", t === tab);
        });
        Array.prototype.forEach.call(
          block.querySelectorAll(".base-view"),
          function (v) { v.hidden = v.getAttribute("data-view") !== name; });
      });
    });
  });
})();
