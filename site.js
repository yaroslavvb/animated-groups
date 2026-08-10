(() => {
  const button = document.querySelector('.motion-toggle');
  if (!button) return;

  const animatedImages = [...document.querySelectorAll('.media img[src$=".gif"]')];
  let paused = false;

  function snapshot(image) {
    const canvas = document.createElement('canvas');
    canvas.width = image.naturalWidth || image.width;
    canvas.height = image.naturalHeight || image.height;
    canvas.setAttribute('aria-hidden', 'true');
    canvas.className = 'motion-snapshot';
    canvas.getContext('2d').drawImage(image, 0, 0, canvas.width, canvas.height);
    image.parentElement.appendChild(canvas);
  }

  function pause() {
    document.querySelectorAll('.motion-snapshot').forEach((canvas) => canvas.remove());
    animatedImages.filter((image) => image.complete).forEach(snapshot);
    document.body.classList.add('is-paused');
    button.setAttribute('aria-pressed', 'true');
    button.querySelector('.pause-icon').textContent = '▶';
    button.querySelector('.motion-label').textContent = 'Play animations';
    paused = true;
  }

  function play() {
    document.body.classList.remove('is-paused');
    document.querySelectorAll('.motion-snapshot').forEach((canvas) => canvas.remove());
    button.setAttribute('aria-pressed', 'false');
    button.querySelector('.pause-icon').textContent = 'Ⅱ';
    button.querySelector('.motion-label').textContent = 'Pause animations';
    paused = false;
  }

  button.addEventListener('click', () => (paused ? play() : pause()));

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    window.addEventListener('load', pause, { once: true });
  }
})();
