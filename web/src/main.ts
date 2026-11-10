// ShahMation Library screen
// search box + list of songs

type Song = {
  music_id: number;
  title: string;
  composer: string | null;
  duration_seconds: number | null;
};

type SongsResponse = {
  total: number;
  songs: Song[];
};

type BoardInfo = {
  connected: boolean;
  board_number: number | null;
  first_note: number | null;
  last_note: number | null;
  simulated: boolean;
};

type PlayerStatus = {
  state: "idle" | "playing" | "paused";
  title: string | null;
  position: number;
  length: number;
  error: string | null;
};

async function post(url: string): Promise<any> {
  const response = await fetch(url, { method: "POST" });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error ?? "Something went wrong");
  }
  return data;
}

const boardBar = document.createElement("div");
boardBar.className = "bar";
const boardStatus = document.createElement("span");
boardStatus.textContent = "Board: not connected";
const connectButton = document.createElement("button");
connectButton.textContent = "Connect";
const panicButton = document.createElement("button");
panicButton.textContent = "PANIC";
panicButton.className = "panic";
boardBar.append(boardStatus, connectButton, panicButton);

const keyCheckHeading = document.createElement("h2");
keyCheckHeading.textContent = "Key Check";
const noteBox = document.createElement("input");
noteBox.type = "number";
noteBox.className = "note";
noteBox.value = "21";
const testButton = document.createElement("button");
testButton.textContent = "Test";
const keyCheckStatus = document.createElement("p");

const nowBar = document.createElement("div");
nowBar.className = "bar";
const nowTitle = document.createElement("span");
nowTitle.textContent = "Nothing playing";
const nowTime = document.createElement("span");
const pauseButton = document.createElement("button");
pauseButton.textContent = "Pause";
const stopButton = document.createElement("button");
stopButton.textContent = "Stop";
const nowError = document.createElement("p");
nowBar.append(nowTitle, nowTime, pauseButton, stopButton);

// build the page
const heading = document.createElement("h1");
heading.textContent = "ShahMation Library";

const searchBox = document.createElement("input");
searchBox.type = "search";
searchBox.placeholder = "Search by title or composer";

// upload a midi file
const addLabel = document.createElement("label");
addLabel.append("Add MIDI ");
const fileInput = document.createElement("input");
fileInput.type = "file";
fileInput.accept = ".mid,.midi";
addLabel.appendChild(fileInput);

const uploadStatus = document.createElement("p");

const statusLine = document.createElement("p");

const table = document.createElement("table");
const headerRow = table.createTHead().insertRow();
for (const name of ["Title", "Composer", "Length"]) {
  const th = document.createElement("th");
  th.textContent = name;
  headerRow.appendChild(th);
}
const tableBody = table.createTBody();
const songList = document.createElement("div");
songList.className = "songs";
songList.appendChild(table);

document.body.append(
  boardBar,
  nowBar,
  nowError,
  keyCheckHeading,
  noteBox,
  testButton,
  keyCheckStatus,
  heading,
  addLabel,
  uploadStatus,
  searchBox,
  statusLine,
  songList,
);

// seconds to minutes with a dash as placeholder if value cannot be determined
function formatLength(seconds: number | null): string {
  if (seconds === null) {
    return "–";
  }
  const minutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return minutes + ":" + String(secs).padStart(2, "0");
}

function showSongs(songs: Song[]) {
  tableBody.innerHTML = ""; // clear out the old rows
  for (const song of songs) {
    const row = tableBody.insertRow();
    // using textContent so an odd song title shows up as text
    row.insertCell().textContent = song.title;
    row.insertCell().textContent = song.composer ?? "";
    row.insertCell().textContent = formatLength(song.duration_seconds);
    row.addEventListener("click", () => playSong(song));
  }
}

async function search(query: string) {
  try {
    const response = await fetch("/api/songs?q=" + encodeURIComponent(query));
    if (!response.ok) {
      throw new Error("bad response");
    }
    const data: SongsResponse = await response.json();

    // if the user kept typing while this was loading answer gets skipped
    if (query !== searchBox.value.trim()) {
      return;
    }

    showSongs(data.songs);
    if (data.total === 0) {
      statusLine.textContent = "No songs match '" + query + "'";
    } else {
      statusLine.textContent =
        "Showing " +
        data.songs.length.toLocaleString() +
        " of " +
        data.total.toLocaleString() +
        " songs";
    }
  } catch {
    // an old search failing does not hide new results
    if (query !== searchBox.value.trim()) {
      return;
    }
    // keep whatever songs were already showing
    statusLine.textContent = "Couldn't load the library";
  }
}

// wait until the user stops typing for 250ms
let typingTimer: number | undefined;
searchBox.addEventListener("input", () => {
  clearTimeout(typingTimer);
  typingTimer = setTimeout(() => search(searchBox.value.trim()), 250);
});

// send the chosen file to the server
fileInput.addEventListener("change", async () => {
  const file = fileInput.files?.[0];
  if (!file) {
    return;
  }
  if (file.size > 2 * 1024 * 1024) {
    uploadStatus.textContent = "The file is too big (2 MB max)";
    fileInput.value = "";
    return;
  }
  uploadStatus.textContent = "Adding " + file.name + "…";
  try {
    const response = await fetch(
      "/api/songs/upload?name=" + encodeURIComponent(file.name),
      {
        method: "POST",
        body: file,
      },
    );
    const data = await response.json();
    if (response.ok) {
      uploadStatus.textContent = "Added '" + data.title + "'";
      // show the new song by searching for it
      searchBox.value = data.title;
      search(data.title);
    } else {
      uploadStatus.textContent = data.error;
    }
  } catch {
    uploadStatus.textContent = "Couldn't add the file";
  }
  // so the same file can be picked again
  fileInput.value = "";
});


let boardMessage = "";

function showBoard(info: BoardInfo) {
  if (info.connected && info.simulated) {
    boardStatus.textContent =
      "Simulated piano connected · " + ((info.last_note ?? 0) - (info.first_note ?? 0) + 1) + " keys";
  } else if (info.connected) {
    boardStatus.textContent =
      "Board " + info.board_number + " connected (notes " + info.first_note + " to " + info.last_note + ")";
  } else {
    boardStatus.textContent = boardMessage || "Board: not connected";
  }
}

connectButton.addEventListener("click", async () => {
  boardStatus.textContent = "Connecting…";
  boardMessage = "";
  try {
    showBoard(await post("/api/board/connect"));
  } catch (e) {
    boardMessage = (e as Error).message;
    boardStatus.textContent = boardMessage;
  }
});

panicButton.addEventListener("click", async () => {
  boardMessage = "PANIC: all off. Press Connect to play again";
  try {
    showBoard(await post("/api/panic"));
  } catch {
    boardStatus.textContent = "Couldn't reach the server";
  }
  refresh();
});

testButton.addEventListener("click", async () => {
  keyCheckStatus.textContent = "Testing note " + noteBox.value + "…";
  try {
    await post("/api/board/test?note=" + encodeURIComponent(noteBox.value));
    keyCheckStatus.textContent = "Played note " + noteBox.value;
  } catch (e) {
    keyCheckStatus.textContent = (e as Error).message;
  }
});


async function playSong(song: Song) {
  nowError.textContent = "";
  try {
    showPlayer(await post("/api/play?music_id=" + song.music_id));
  } catch (e) {
    nowError.textContent = (e as Error).message;
  }
}

function showPlayer(status: PlayerStatus) {
  if (status.state === "idle") {
    nowTitle.textContent = status.title ? "Finished: " + status.title : "Nothing playing";
  } else {
    nowTitle.textContent = "Now performing: " + status.title;
  }
  nowTime.textContent = formatLength(status.position) + " / " + formatLength(status.length);
  pauseButton.textContent = status.state === "paused" ? "Resume" : "Pause";
  pauseButton.disabled = status.state === "idle";
  stopButton.disabled = status.state === "idle";
  if (status.error) {
    nowError.textContent = status.error;
  }
}

async function refresh() {
  try {
    const info: BoardInfo = await (await fetch("/api/board")).json();
    const status: PlayerStatus = await (await fetch("/api/player")).json();
    showBoard(info);
    showPlayer(status);
  } catch {
  }
}

pauseButton.addEventListener("click", async () => {
  const url = pauseButton.textContent === "Resume" ? "/api/resume" : "/api/pause";
  showPlayer(await post(url));
});

stopButton.addEventListener("click", async () => {
  showPlayer(await post("/api/stop"));
});

// show everything when the page first opens
search("");
refresh();
setInterval(refresh, 500);
