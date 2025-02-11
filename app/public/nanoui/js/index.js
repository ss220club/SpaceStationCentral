function displayPlayerInfo(playerData) {
  const uiContent = document.getElementById("uiContent");
  uiContent.innerHTML = `
      <div>Ckey: ${playerData.ckey}</div>
      <div>Discord ID: ${playerData.discord_id}</div>
    `;
}

function displayError(error) {
  const uiContent = document.getElementById("uiContent");
  uiContent.innerHTML = `Error: ${error.message}`;
}

function fetchPlayer() {
  const ckeyInput = document.getElementById("ckeyInput");
  const ckey = ckeyInput.value.trim();
  const uiContent = document.getElementById("uiContent");

  if (!ckey) {
    displayError(new Error("Please enter a ckey"));
    return;
  }

  uiContent.innerHTML = "Loading...";

  fetch(`/v1/players/ckey/${ckey}`)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then(displayPlayerInfo)
    .catch(displayError);
}

function toggleAudio() {
  const bg_audio = document.getElementById("backgroundMusic");
  bg_audio.muted = !bg_audio.muted;
  bg_audio.play()
  bg_audio.currentTime = 84;
}