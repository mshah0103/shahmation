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
      document.body.append(heading, addLabel, uploadStatus, searchBox, statusLine, table);
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
          uploadStatus.textContent = "That file is too big (2 MB max)";
          fileInput.value = "";
          return;
        }
        uploadStatus.textContent = "Adding " + file.name + "\u2026";
        try {
          const response = await fetch("/api/songs/upload?name=" + encodeURIComponent(file.name), {
            method: "POST",
            body: file
          });
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
      search("");
    }
  });
  require_main();
})();
