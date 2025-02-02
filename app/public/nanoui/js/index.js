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

  fetch(`http://127.0.0.1:8000/v1/player?ckey=${encodeURIComponent(ckey)}`)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then(displayPlayerInfo)
    .catch(displayError);
}
