(() => {
  const button = document.querySelector('.motion-toggle');
  const status = document.querySelector('.motion-status');
  const images = [...document.querySelectorAll('.motion-image')];
  const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
  let paused = preference.matches;
  let userOverride = false;

  function addSnapshot(image) {
    const media = image.closest('.media');
    if (!media || media.querySelector('.motion-snapshot') || !image.naturalWidth) return;

    const canvas = document.createElement('canvas');
    canvas.className = 'motion-snapshot';
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    canvas.setAttribute('aria-hidden', 'true');
    canvas.getContext('2d').drawImage(image, 0, 0);
    media.appendChild(canvas);
  }

  function removeSnapshots() {
    document.querySelectorAll('.motion-snapshot').forEach((canvas) => canvas.remove());
  }

  function renderState() {
    if (paused) {
      images.forEach((image) => {
        if (image.complete) addSnapshot(image);
      });
    } else {
      removeSnapshots();
    }

    button.setAttribute('aria-pressed', String(paused));
    button.querySelector('.motion-icon').textContent = paused ? '▶' : 'Ⅱ';
    button.querySelector('.motion-label').textContent = paused ? 'Play animations' : 'Pause animations';
    status.textContent = paused ? 'Animations paused.' : 'Animations playing.';
  }

  images.forEach((image) => image.addEventListener('load', () => {
    if (paused) addSnapshot(image);
  }));

  button.addEventListener('click', () => {
    userOverride = true;
    paused = !paused;
    renderState();
  });

  preference.addEventListener('change', (event) => {
    if (!userOverride) {
      paused = event.matches;
      renderState();
    }
  });

  renderState();
})();
