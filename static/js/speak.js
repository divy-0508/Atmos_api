// speak.js — speakText accepts either a string (text) or will read the element text if it's an id
function speakText(textOrId) {
  let text = "";

  // if element with id exists, read its innerText
  const el = document.getElementById(textOrId);
  if (el) {
    text = el.innerText.trim();
  } else {
    text = String(textOrId || "");
  }

  if (!("speechSynthesis" in window)) {
    alert("Text-to-speech not supported in your browser.");
    return;
  }

  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "en-US";
  u.rate = 1;
  u.pitch = 1;
  window.speechSynthesis.speak(u);
}
