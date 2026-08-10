(() => {
  const FRAME_COUNT = 60;
  const FPS = 20;
  const globalButton = document.querySelector('.motion-toggle');
  const status = document.querySelector('.motion-status');
  const images = [...document.querySelectorAll('.motion-image')];

  if (!globalButton || !status || !images.length) return;

  const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
  let userOverride = false;
  let intersectionObserver = null;
  let phaseAnimationFrame = null;

  function contextualName(image, figure) {
    const motif = figure.querySelector('figcaption')?.textContent.trim() || 'motif';
    const symmetry = figure.closest('.symmetry')?.querySelector('h2')?.textContent.trim()
      || 'spacetime action';
    return `${motif} — ${symmetry}`.replace(/\s+/g, ' ');
  }

  function createElement(tag, className, text = '') {
    const element = document.createElement(tag);
    element.className = className;
    element.textContent = text;
    return element;
  }

  function initializePlayer(image, index) {
    const figure = image.closest('figure');
    const media = image.closest('.media');
    const posterSrc = image.dataset.posterSrc;
    const gifSrc = image.dataset.motionSrc;
    const videoSrc = image.dataset.videoSrc;

    if (!figure || !media || !posterSrc || !gifSrc || !videoSrc) {
      console.error(`Animation ${index + 1} is missing its media metadata.`);
      return null;
    }

    const name = contextualName(image, figure);
    const mediaId = `animation-media-${index + 1}`;
    const sliderId = `animation-phase-${index + 1}`;
    const caption = figure.querySelector('figcaption');
    if (caption && !caption.id) caption.id = `animation-caption-${index + 1}`;

    const video = document.createElement('video');
    video.id = mediaId;
    video.className = 'motion-video';
    video.poster = posterSrc;
    video.preload = 'none';
    video.muted = true;
    video.defaultMuted = true;
    video.loop = true;
    video.playsInline = true;
    video.setAttribute('muted', '');
    video.setAttribute('playsinline', '');
    video.width = Number(image.getAttribute('width')) || 600;
    video.height = Number(image.getAttribute('height')) || 600;
    video.setAttribute('aria-label', image.getAttribute('alt') || name);
    if (caption) video.setAttribute('aria-describedby', caption.id);

    const controls = createElement('div', 'animation-controls');
    controls.setAttribute('role', 'group');
    controls.setAttribute('aria-label', `Animation controls for ${name}`);

    const toggle = createElement('button', 'animation-toggle');
    toggle.type = 'button';
    toggle.setAttribute('aria-controls', mediaId);
    const icon = createElement('span', 'animation-icon', '▶');
    icon.setAttribute('aria-hidden', 'true');
    const label = createElement('span', 'animation-label', 'Play');
    toggle.append(icon, label);

    const slider = createElement('input', 'phase-slider');
    slider.id = sliderId;
    slider.type = 'range';
    slider.min = '0';
    slider.max = String(FRAME_COUNT - 1);
    slider.step = '1';
    slider.value = '0';
    slider.setAttribute('aria-controls', mediaId);
    slider.setAttribute('aria-label', `Animation phase for ${name}`);

    const output = createElement('output', 'phase-output', `01 / ${FRAME_COUNT}`);
    output.setAttribute('for', sliderId);
    controls.append(toggle, slider, output);

    image.hidden = true;
    media.append(video);
    figure.append(controls);

    return {
      index,
      name,
      figure,
      media,
      image,
      video,
      videoSrc,
      gifSrc,
      controls,
      toggle,
      icon,
      label,
      slider,
      output,
      wantsPlay: !preference.matches,
      nearViewport: false,
      loaded: false,
      loading: null,
      error: false,
      pendingFrame: null,
      currentFrame: null,
    };
  }

  const players = images.map(initializePlayer).filter(Boolean);
  if (!players.length) return;

  function phaseText(frame) {
    return `Frame ${frame + 1} of ${FRAME_COUNT}; phase ${frame}/${FRAME_COUNT}`;
  }

  function updatePhase(player, frame) {
    const bounded = Math.max(0, Math.min(FRAME_COUNT - 1, Math.round(frame)));
    if (player.currentFrame === bounded) return;
    player.currentFrame = bounded;
    if (player.slider.value !== String(bounded)) player.slider.value = String(bounded);
    player.slider.setAttribute('aria-valuetext', phaseText(bounded));
    player.output.textContent = `${String(bounded + 1).padStart(2, '0')} / ${FRAME_COUNT}`;
  }

  function frameFromTime(video) {
    const rawFrame = Math.floor((video.currentTime * FPS) + 1e-6);
    return ((rawFrame % FRAME_COUNT) + FRAME_COUNT) % FRAME_COUNT;
  }

  function availablePlayers() {
    return players.filter((player) => !player.error);
  }

  function renderGlobalState() {
    const available = availablePlayers();
    if (!available.length) {
      globalButton.querySelector('.motion-icon').textContent = '×';
      globalButton.querySelector('.motion-label').textContent = 'Animations unavailable';
      globalButton.disabled = true;
      return;
    }

    globalButton.disabled = false;
    const anyRequested = available.some((player) => player.wantsPlay);
    globalButton.querySelector('.motion-icon').textContent = anyRequested ? '■' : '▶';
    globalButton.querySelector('.motion-label').textContent = (
      anyRequested ? 'Stop all animations' : 'Play all animations'
    );
  }

  function renderPlayerState(player) {
    if (player.error) {
      player.icon.textContent = '×';
      player.label.textContent = 'Unavailable';
      player.toggle.disabled = true;
      player.slider.disabled = true;
      player.toggle.setAttribute('aria-label', `Animation unavailable for ${player.name}`);
      player.controls.dataset.state = 'error';
      player.media.dataset.state = 'error';
      return;
    }

    const requested = player.wantsPlay;
    player.icon.textContent = requested ? '■' : '▶';
    player.label.textContent = requested ? 'Pause' : 'Play';
    player.toggle.setAttribute(
      'aria-label',
      `${requested ? 'Pause' : 'Play'} animation for ${player.name}`,
    );
    player.controls.dataset.state = requested ? 'playing' : 'paused';
    player.media.dataset.state = requested ? 'playing' : 'paused';
  }

  function markUnavailable(player, message) {
    if (player.error) return;
    player.error = true;
    player.wantsPlay = false;
    player.video.pause();
    player.video.hidden = true;
    player.image.hidden = false;
    player.image.setAttribute('src', player.image.dataset.posterSrc);
    renderPlayerState(player);
    renderGlobalState();
    status.textContent = message;
    console.error(message);
  }

  function applyPendingFrame(player) {
    if (player.pendingFrame === null || !player.loaded) return;
    const frame = player.pendingFrame;
    player.pendingFrame = null;
    player.video.currentTime = frame / FPS;
    updatePhase(player, frame);
  }

  function ensureLoaded(player) {
    if (player.error) return Promise.reject(new Error(`${player.name} is unavailable.`));
    if (player.loaded) return Promise.resolve(player);
    if (player.loading) return player.loading;

    player.media.dataset.state = 'loading';
    player.loading = new Promise((resolve, reject) => {
      const handleLoaded = () => {
        cleanup();
        player.loaded = true;
        player.loading = null;
        applyPendingFrame(player);
        renderPlayerState(player);
        resolve(player);
      };
      const handleError = () => {
        cleanup();
        player.loading = null;
        const error = new Error(`Unable to load the playback proxy for ${player.name}.`);
        markUnavailable(player, error.message);
        reject(error);
      };
      const cleanup = () => {
        player.video.removeEventListener('loadedmetadata', handleLoaded);
        player.video.removeEventListener('error', handleError);
      };

      player.video.addEventListener('loadedmetadata', handleLoaded);
      player.video.addEventListener('error', handleError);
      player.video.src = player.videoSrc;
      player.video.load();
    });
    return player.loading;
  }

  async function playPlayer(
    player,
    { announceFailure = true, userInitiated = false } = {},
  ) {
    if (player.error) return;
    if (userInitiated) player.nearViewport = true;
    player.wantsPlay = true;
    renderPlayerState(player);
    renderGlobalState();
    if (!player.nearViewport || document.hidden) return;

    try {
      const loading = ensureLoaded(player);
      const playback = player.video.play();
      await Promise.all([loading, playback]);
      if (!player.wantsPlay || !player.nearViewport || document.hidden) {
        suspendPlayer(player);
      } else if (announceFailure) {
        status.textContent = `${player.name} playing.`;
      }
    } catch (error) {
      if (
        !player.error
        && player.wantsPlay
      ) {
        player.wantsPlay = false;
        renderPlayerState(player);
        renderGlobalState();
        if (announceFailure) {
          status.textContent = `${player.name} could not be started.`;
        }
        console.error(error);
      }
    }
  }

  function pausePlayer(player) {
    if (player.error) return;
    player.wantsPlay = false;
    if (player.loaded) {
      player.video.pause();
      updatePhase(player, frameFromTime(player.video));
    }
    renderPlayerState(player);
    renderGlobalState();
  }

  function suspendPlayer(player) {
    if (player.loaded && !player.video.paused) player.video.pause();
  }

  function seekPlayer(player, frame) {
    if (player.error) return;
    pausePlayer(player);
    player.pendingFrame = frame;
    updatePhase(player, frame);
    ensureLoaded(player)
      .then(() => applyPendingFrame(player))
      .catch(() => {});
  }

  players.forEach((player) => {
    updatePhase(player, 0);
    renderPlayerState(player);

    player.toggle.addEventListener('click', () => {
      userOverride = true;
      if (player.wantsPlay) {
        pausePlayer(player);
        status.textContent = `${player.name} stopped.`;
      } else {
        playPlayer(player, { userInitiated: true });
        status.textContent = `${player.name} starting.`;
      }
    });

    player.slider.addEventListener('input', () => {
      userOverride = true;
      seekPlayer(player, Number(player.slider.value));
    });

    player.slider.addEventListener('change', () => {
      const frame = Number(player.slider.value);
      status.textContent = `${player.name} stopped at ${phaseText(frame).toLowerCase()}.`;
    });

    player.video.addEventListener('play', () => {
      renderPlayerState(player);
      renderGlobalState();
      schedulePhaseUpdates();
    });
    player.video.addEventListener('pause', () => {
      if (player.loaded) updatePhase(player, frameFromTime(player.video));
    });
    player.video.addEventListener('seeked', () => {
      updatePhase(player, frameFromTime(player.video));
    });
    player.video.addEventListener('error', () => {
      if (player.loaded && !player.error) {
        markUnavailable(player, `Playback failed for ${player.name}.`);
      }
    });
  });

  function updatePlayingPhases() {
    phaseAnimationFrame = null;
    let anyPlaying = false;
    players.forEach((player) => {
      if (player.loaded && !player.video.paused && !player.video.seeking) {
        anyPlaying = true;
        updatePhase(player, frameFromTime(player.video));
      }
    });
    if (anyPlaying) schedulePhaseUpdates();
  }

  function schedulePhaseUpdates() {
    if (phaseAnimationFrame === null) {
      phaseAnimationFrame = window.requestAnimationFrame(updatePlayingPhases);
    }
  }

  function observePlayers() {
    if (!('IntersectionObserver' in window)) {
      players.forEach((player) => {
        player.nearViewport = true;
        ensureLoaded(player)
          .then(() => {
            if (player.wantsPlay) playPlayer(player, { announceFailure: false });
          })
          .catch(() => {});
      });
      return;
    }

    intersectionObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        const player = players.find((candidate) => candidate.figure === entry.target);
        if (!player || player.error) return;
        player.nearViewport = entry.isIntersecting;
        if (entry.isIntersecting) {
          ensureLoaded(player)
            .then(() => {
              if (player.wantsPlay) playPlayer(player, { announceFailure: false });
            })
            .catch(() => {});
        } else {
          suspendPlayer(player);
        }
      });
    }, { rootMargin: '400px 0px' });
    players.forEach((player) => intersectionObserver.observe(player.figure));
  }

  globalButton.addEventListener('click', () => {
    userOverride = true;
    const available = availablePlayers();
    if (!available.length) {
      status.textContent = 'Animation playback is unavailable.';
      renderGlobalState();
      return;
    }

    const shouldPlay = !available.some((player) => player.wantsPlay);
    available.forEach((player) => {
      if (shouldPlay) {
        playPlayer(player, { announceFailure: false });
      } else {
        pausePlayer(player);
      }
    });
    status.textContent = shouldPlay ? 'All animations playing.' : 'All animations stopped.';
    renderGlobalState();
  });

  const handlePreferenceChange = (event) => {
    if (userOverride) return;
    availablePlayers().forEach((player) => {
      if (event.matches) pausePlayer(player);
      else playPlayer(player, { announceFailure: false });
    });
    status.textContent = event.matches
      ? 'Animations stopped for reduced motion.'
      : 'Animations playing.';
  };

  if (typeof preference.addEventListener === 'function') {
    preference.addEventListener('change', handlePreferenceChange);
  } else {
    preference.addListener(handlePreferenceChange);
  }

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      players.forEach(suspendPlayer);
    } else {
      availablePlayers().forEach((player) => {
        if (player.wantsPlay && player.nearViewport) {
          playPlayer(player, { announceFailure: false });
        }
      });
    }
  });

  globalButton.removeAttribute('aria-pressed');
  renderGlobalState();
  globalButton.hidden = false;
  observePlayers();
})();
