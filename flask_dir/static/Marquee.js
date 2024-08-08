window.addEventListener('load', doAll);
window.addEventListener('resize', doAll);

function resizeTitle() {resizeFont("keyText1", "replaced1");}
function resizeArtist() {resizeFont("keyText2", "replaced2");}
function setRepeat() {repeatHeight("marqueeright", "marqueeleft", "fill", 15);}
function doAll() {
  resizeTitle();
  resizeArtist();
  setRepeat();
}



function resizeFont(textToReplace, replacedText) {
  let key = document.getElementById(textToReplace);
  let content = key.textContent;
  let elements = document.getElementsByClassName(replacedText);

  for (let i = 0; i < elements.length; i++) {
  let cs = getComputedStyle(elements[i]);
  let fontFam = cs.getPropertyValue("font-family");
  var fontSize = cs.getPropertyValue("font-size");

  canvas = document.createElement("canvas");
  context = canvas.getContext("2d");
  var font = fontSize + " " + fontFam + " "
  context.font = font;

  var currentWidth = context.measureText(content).width;

  let windowWidth = window.innerWidth;
  var currentCount = windowWidth / currentWidth;
  var fontSizeNum = parseInt(fontSize, 10);
  while (currentCount % 1 > 0.5) {
    if (fontSizeNum > (innerWidth/20)) {
    fontSizeNum = (innerWidth/30);
    }
    fontSizeNum = fontSizeNum + 0.01;
    font = fontSizeNum + "px " + fontFam
    context.font = font;
    currentWidth = context.measureText(content).width;
    currentCount = windowWidth / currentWidth;
    }
  let spacedContent = "&nbsp;" + content.trim();

  elements[i].innerHTML = (spacedContent.repeat(Math.ceil(currentCount))).trim();
  elements[i].style.fontSize = fontSizeNum + "px";
  }
}


function repeatHeight(replaced1, replaced2, fillDiv, spacer) {

  let elements1 = document.getElementsByClassName(replaced1);
  let content1 = replaced1.textContent;

  let elements2 = document.getElementsByClassName(replaced2);
  let content2 = replaced2.textContent;

  let i = 0;
    // get both computed styles
  let cs1 = getComputedStyle(elements1[i]);
  let cs2 = getComputedStyle(elements2[i]);

  // get fonts
  let fontFam1 = cs1.getPropertyValue("font-family");
  var fontSize1 = cs1.getPropertyValue("font-size");

  let fontFam2 = cs2.getPropertyValue("font-family");
  var fontSize2 = cs2.getPropertyValue("font-size");

  canvas = document.createElement("canvas");
  context = canvas.getContext("2d");

  // create two fonts
  var font1 = fontSize1 + " " + fontFam1 + " "

  var font2 = fontSize2 + " " + fontFam2 + " "

  context.font = font1;
  var metrics1 = context.measureText(content1);
  let currentHeight1 = metrics1.actualBoundingBoxAscent + metrics1.actualBoundingBoxDescent;

  context.font = font2;
  var metrics2 = context.measureText(content2);
  let currentHeight2 = metrics2.actualBoundingBoxAscent + metrics2.actualBoundingBoxDescent;

  let windowHeight = window.innerHeight;
  //document.getElementById(fillDiv).innerHTML = windowHeight;


  var currentCount = 1;
  while ((currentCount * (currentHeight1 + spacer + currentHeight2 + spacer)) < windowHeight) {
    currentCount = currentCount + 1;
  }

  for (let num = 0; num < currentCount; num++) {

    var marLef1 = elements1[0].cloneNode(true);
    marLef1.style.position = 'fixed';
    marLef1.style.top = (spacer + currentHeight2 + ((currentHeight1 + spacer + currentHeight2 + spacer)* num)).toString() + "px";

    var marLef2 = elements1[1].cloneNode(true);
    marLef2.style.position = 'fixed';
    marLef2.style.top = (spacer + currentHeight2 + ((currentHeight1 + spacer + currentHeight2 + spacer)* num)).toString() + "px";

    var marRig1 = elements2[0].cloneNode(true);
    marRig1.style.position = 'fixed';
    marRig1.style.top = ( (currentHeight1 + spacer + currentHeight2 + spacer) * num).toString() + "px";

    var marRig2 = elements2[1].cloneNode(true);
    marRig2.style.position = 'fixed';
    marRig2.style.top = ( (currentHeight1 + spacer + currentHeight2 + spacer) * num).toString() + "px";

    document.getElementById(fillDiv).appendChild(marLef1);
    document.getElementById(fillDiv).appendChild(marLef2);
    document.getElementById(fillDiv).appendChild(marRig1);
    document.getElementById(fillDiv).appendChild(marRig2);
  }
  elements1[0].style.visibility = "hidden"
  elements1[1].style.visibility = "hidden"
  elements2[0].style.visibility = "hidden"
  elements2[1].style.visibility = "hidden"
}