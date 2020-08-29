const btn = document.getElementById("btn");
const model = document.querySelector(".model-section");


btn.addEventListener("click", function(){
    model.style.display = "block";
});

model.addEventListener("click", function(e){
  let className = e.target.getAttribute("class");
  if(className === "model-section"){
      model.style.display = "none";
  }
})
