// ShahMation Library screen (S1)
// Search box + list of songs. Searching happens on the Pi through /api/songs.

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

const statusLine = document.createElement("p");

const table = document.createElement("table");
const headerRow = table.createTHead().insertRow();
for (const name of ["Title", "Composer", "Length"]) {
  const th = document.createElement("th");
  th.textContent = name;
  headerRow.appendChild(th);
}
const tableBody = table.createTBody();

document.body.append(heading, searchBox, statusLine, table);

// 125.4 -> "2:05", and a dash if we don't know the length
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
    // using textContent so a weird song title just shows up as text (TC-R02)
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

    // if the user kept typing while this was loading, this answer is old so skip it
    if (query !== searchBox.value.trim()) {
      return;
    }

    showSongs(data.songs);
    if (data.total === 0) {
      statusLine.textContent = "No songs match '" + query + "'";
    } else {
      statusLine.textContent =
        "Showing " + data.songs.length.toLocaleString() + " of " + data.total.toLocaleString() + " songs";
    }
  } catch {
    // same thing here, an old search failing shouldn't cover up newer results
    if (query !== searchBox.value.trim()) {
      return;
    }
    // keep whatever songs were already showing (slide 21: show error, keep saved data)
    statusLine.textContent = "Couldn't load the library";
  }
}

// wait until the user stops typing for 250ms so we don't search on every key
let typingTimer: number | undefined;
searchBox.addEventListener("input", () => {
  clearTimeout(typingTimer);
  typingTimer = setTimeout(() => search(searchBox.value.trim()), 250);
});

// show everything when the page first opens
search("");
