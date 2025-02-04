document.addEventListener("DOMContentLoaded", function () {
  const items = document.querySelectorAll(".list-header");

  items.forEach((item) => {
    item.addEventListener("click", function () {
      const content = this.nextElementSibling;
      const arrow = this.querySelector(".arrow");

      if (content.style.display === "block") {
        content.style.display = "none";
        arrow.style.transform = "rotate(0deg)";
      } else {
        document.querySelectorAll(".list-content").forEach((el) => {
          el.style.display = "none";
        });

        document.querySelectorAll(".arrow").forEach((el) => {
          el.style.transform = "rotate(0deg)";
        });

        content.style.display = "block";
        arrow.style.transform = "rotate(180deg)";
      }
    });
  });
});
