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

document.body.append(
  heading,
  addLabel,
  uploadStatus,
  searchBox,
  statusLine,
  table,
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

// show everything when the page first opens
search("");
