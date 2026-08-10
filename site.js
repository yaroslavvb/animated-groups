(() => {
  const button = document.querySelector('.motion-toggle');
  const status = document.querySelector('.motion-status');
  const images = [...document.querySelectorAll('.motion-image')];

  if (!button || !status || !images.length) return;

  const hasGifSources = images.every((image) => (
    image.dataset.posterSrc && image.dataset.motionSrc
  ));
  if (!hasGifSources) {
    console.error('Motion controls require poster and animated sources for every image.');
    return;
  }

  function startLegacyControls() {
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
    let playing = !preference.matches;
    let userOverride = false;

    function renderState({ announce = false } = {}) {
      images.forEach((image) => {
        const source = playing ? image.dataset.motionSrc : image.dataset.posterSrc;
        image.hidden = false;
        if (image.getAttribute('src') !== source) image.setAttribute('src', source);
      });

      button.querySelector('.motion-icon').textContent = playing ? '■' : '▶';
      button.querySelector('.motion-label').textContent = (
        playing ? 'Stop all animations' : 'Play all animations'
      );
      if (announce) {
        status.textContent = playing ? 'All animations playing.' : 'All animations stopped.';
      }
    }

    button.addEventListener('click', () => {
      userOverride = true;
      playing = !playing;
      renderState({ announce: true });
    });

    const handlePreferenceChange = (event) => {
      if (userOverride) return;
      playing = !event.matches;
      renderState({ announce: true });
    };

    if (typeof preference.addEventListener === 'function') {
      preference.addEventListener('change', handlePreferenceChange);
    } else {
      preference.addListener(handlePreferenceChange);
    }

    button.removeAttribute('aria-pressed');
    renderState();
    button.hidden = false;
  }

  if (images.every((image) => image.dataset.videoSrc)) {
    const controller = document.createElement('script');
    controller.src = 'site-controls-v2.js';
    controller.addEventListener('error', startLegacyControls, { once: true });
    document.head.append(controller);
    return;
  }

  startLegacyControls();
})();
