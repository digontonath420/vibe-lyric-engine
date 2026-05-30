function searchSong() {
    const query = document.getElementById('searchQuery').value.trim();
    if (!query) return alert('Please enter a song name!');

    const loader = document.getElementById('loader');
    const resultsContainer = document.getElementById('resultsContainer');
    const resultsList = document.getElementById('resultsList');
    const downloadContainer = document.getElementById('downloadContainer');

    loader.classList.remove('hidden');
    document.getElementById('loaderText').innerText = "Searching global servers for tracks...";
    resultsContainer.classList.add('hidden');
    downloadContainer.classList.add('hidden');
    resultsList.innerHTML = '';

    fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query })
    })
    .then(res => res.json())
    .then(data => {
        loader.classList.add('hidden');
        if (data.error) {
            alert('Error: ' + data.error);
            return;
        }
        if (!data.results || data.results.length === 0) {
            alert('No tracks found. Try different keywords.');
            return;
        }
        resultsContainer.classList.remove('hidden');
        data.results.forEach(track => {
            const item = document.createElement('div');
            item.className = 'result-item';
            item.onclick = () => generateVideo(track.id, track.title);
            item.innerHTML = `
                <div class="track-info">
                    <div class="track-title">${track.title}</div>
                    <div class="track-url">Source: YouTube Audio Pipeline</div>
                </div>
                <button class="btn-select">Render</button>
            `;
            resultsList.appendChild(item);
        });
    })
    .catch(err => {
        loader.classList.add('hidden');
        alert('Network or server error. Please try again.');
        console.error(err);
    });
}

function generateVideo(trackId, trackTitle) {
    const fontStyle = document.getElementById('fontStyle').value;
    const bgStyle = document.getElementById('bgStyle').value;
    const loader = document.getElementById('loader');
    const resultsContainer = document.getElementById('resultsContainer');
    const downloadContainer = document.getElementById('downloadContainer');

    loader.classList.remove('hidden');
    document.getElementById('loaderText').innerText = "Downloading HQ Audio & Syncing Lyrics (Takes 15-30 secs)...";
    resultsContainer.classList.add('hidden');
    downloadContainer.classList.add('hidden');

    fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            id: trackId,
            title: trackTitle,
            font_style: fontStyle,
            bg_style: bgStyle
        })
    })
    .then(res => res.json())
    .then(data => {
        loader.classList.add('hidden');
        if (data.error) {
            alert('Rendering failed: ' + data.error + (data.details ? '\n' + data.details : ''));
            return;
        }
        downloadContainer.classList.remove('hidden');
        document.getElementById('renderedTitle').innerText = `"${data.title}" processed with selected typography overlay.`;
        document.getElementById('downloadLink').href = data.download_url;
    })
    .catch(err => {
        loader.classList.add('hidden');
        alert('Processing error or timeout. Free tier node may be slow.');
        console.error(err);
    });
}
