"use strict";
(() => {
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __commonJS = (cb, mod) => function __require() {
    try {
      return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
    } catch (e) {
      throw mod = 0, e;
    }
  };

  // src/main.ts
  var require_main = __commonJS({
    "src/main.ts"() {
      async function post(url) {
        const response = await fetch(url, { method: "POST" });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.error ?? "Something went wrong");
        }
        return data;
      }
      var boardBar = document.createElement("div");
      boardBar.className = "bar";
      var boardStatus = document.createElement("span");
      boardStatus.textContent = "Board: not connected";
      var connectButton = document.createElement("button");
      connectButton.textContent = "Connect";
      var panicButton = document.createElement("button");
      panicButton.textContent = "PANIC";
      panicButton.className = "panic";
      boardBar.append(boardStatus, connectButton, panicButton);
      var keyCheckHeading = document.createElement("h2");
      keyCheckHeading.textContent = "Key Check";
      var noteBox = document.createElement("input");
      noteBox.type = "number";
      noteBox.className = "note";
      noteBox.value = "21";
      var testButton = document.createElement("button");
      testButton.textContent = "Test";
      var keyCheckStatus = document.createElement("p");
      var nowBar = document.createElement("div");
      nowBar.className = "bar";
      var nowTitle = document.createElement("span");
      nowTitle.textContent = "Nothing playing";
      var nowTime = document.createElement("span");
      var pauseButton = document.createElement("button");
      pauseButton.textContent = "Pause";
      var stopButton = document.createElement("button");
      stopButton.textContent = "Stop";
      var nowError = document.createElement("p");
      nowBar.append(nowTitle, nowTime, pauseButton, stopButton);
      var heading = document.createElement("h1");
      heading.textContent = "ShahMation Library";
      var searchBox = document.createElement("input");
      searchBox.type = "search";
      searchBox.placeholder = "Search by title or composer";
      var addLabel = document.createElement("label");
      addLabel.append("Add MIDI ");
      var fileInput = document.createElement("input");
      fileInput.type = "file";
      fileInput.accept = ".mid,.midi";
      addLabel.appendChild(fileInput);
      var uploadStatus = document.createElement("p");
      var statusLine = document.createElement("p");
      var table = document.createElement("table");
      var headerRow = table.createTHead().insertRow();
      for (const name of ["Title", "Composer", "Length"]) {
        const th = document.createElement("th");
        th.textContent = name;
        headerRow.appendChild(th);
      }
      var tableBody = table.createTBody();
      var songList = document.createElement("div");
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
        songList
      );
      function formatLength(seconds) {
        if (seconds === null) {
          return "\u2013";
        }
        const minutes = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return minutes + ":" + String(secs).padStart(2, "0");
      }
      function showSongs(songs) {
        tableBody.innerHTML = "";
        for (const song of songs) {
          const row = tableBody.insertRow();
          row.insertCell().textContent = song.title;
          row.insertCell().textContent = song.composer ?? "";
          row.insertCell().textContent = formatLength(song.duration_seconds);
          row.addEventListener("click", () => playSong(song));
        }
      }
      async function search(query) {
        try {
          const response = await fetch("/api/songs?q=" + encodeURIComponent(query));
          if (!response.ok) {
            throw new Error("bad response");
          }
          const data = await response.json();
          if (query !== searchBox.value.trim()) {
            return;
          }
          showSongs(data.songs);
          if (data.total === 0) {
            statusLine.textContent = "No songs match '" + query + "'";
          } else {
            statusLine.textContent = "Showing " + data.songs.length.toLocaleString() + " of " + data.total.toLocaleString() + " songs";
          }
        } catch {
          if (query !== searchBox.value.trim()) {
            return;
          }
          statusLine.textContent = "Couldn't load the library";
        }
      }
      var typingTimer;
      searchBox.addEventListener("input", () => {
        clearTimeout(typingTimer);
        typingTimer = setTimeout(() => search(searchBox.value.trim()), 250);
      });
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
        uploadStatus.textContent = "Adding " + file.name + "\u2026";
        try {
          const response = await fetch(
            "/api/songs/upload?name=" + encodeURIComponent(file.name),
            {
              method: "POST",
              body: file
            }
          );
          const data = await response.json();
          if (response.ok) {
            uploadStatus.textContent = "Added '" + data.title + "'";
            searchBox.value = data.title;
            search(data.title);
          } else {
            uploadStatus.textContent = data.error;
          }
        } catch {
          uploadStatus.textContent = "Couldn't add the file";
        }
        fileInput.value = "";
      });
      var boardMessage = "";
      function showBoard(info) {
        if (info.connected && info.simulated) {
          boardStatus.textContent = "Simulated piano connected \xB7 " + ((info.last_note ?? 0) - (info.first_note ?? 0) + 1) + " keys";
        } else if (info.connected) {
          boardStatus.textContent = "Board " + info.board_number + " connected (notes " + info.first_note + " to " + info.last_note + ")";
        } else {
          boardStatus.textContent = boardMessage || "Board: not connected";
        }
      }
      connectButton.addEventListener("click", async () => {
        boardStatus.textContent = "Connecting\u2026";
        boardMessage = "";
        try {
          showBoard(await post("/api/board/connect"));
        } catch (e) {
          boardMessage = e.message;
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
        keyCheckStatus.textContent = "Testing note " + noteBox.value + "\u2026";
        try {
          await post("/api/board/test?note=" + encodeURIComponent(noteBox.value));
          keyCheckStatus.textContent = "Played note " + noteBox.value;
        } catch (e) {
          keyCheckStatus.textContent = e.message;
        }
      });
      async function playSong(song) {
        nowError.textContent = "";
        try {
          showPlayer(await post("/api/play?music_id=" + song.music_id));
        } catch (e) {
          nowError.textContent = e.message;
        }
      }
      function showPlayer(status) {
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
          const info = await (await fetch("/api/board")).json();
          const status = await (await fetch("/api/player")).json();
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
      search("");
      refresh();
      setInterval(refresh, 500);
    }
  });
  require_main();
})();
