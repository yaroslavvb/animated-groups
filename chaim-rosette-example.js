(() => {
  "use strict";

  const COLORS = ["blue", "red", "green"];
  const RAY_COLORS = ["var(--blue)", "var(--red)", "var(--green)"];
  const SUPERSCRIPTS = ["⁰", "¹", "²", "³", "⁴", "⁵"];

  function rotationLabel(power) {
    if (power === 0) return "e";
    if (power === 1) return "r";
    return `r${SUPERSCRIPTS[power]}`;
  }

  function reflectionLabel(power) {
    if (power === 0) return "s";
    if (power === 1) return "sr";
    return `sr${SUPERSCRIPTS[power]}`;
  }

  function operationData() {
    const operations = [];

    for (let coset = 0; coset < 3; coset += 1) {
      const oppositePower = coset + 3;
      const baseAngle = coset * 60;

      operations.push(
        {
          color: COLORS[coset],
          power: coset,
          reflected: false,
          label: rotationLabel(coset),
          positionAngle: baseAngle - 8,
        },
        {
          color: COLORS[coset],
          power: coset,
          reflected: true,
          label: reflectionLabel(coset),
          positionAngle: baseAngle + 8,
        },
        {
          color: COLORS[coset],
          power: oppositePower,
          reflected: false,
          label: rotationLabel(oppositePower),
          positionAngle: baseAngle + 180 - 8,
        },
        {
          color: COLORS[coset],
          power: oppositePower,
          reflected: true,
          label: reflectionLabel(oppositePower),
          positionAngle: baseAngle + 180 + 8,
        },
      );
    }

    return operations;
  }

  function addStructure(stage, mode) {
    const ring = document.createElement("span");
    ring.className = "rosette-ring";
    ring.setAttribute("aria-hidden", "true");
    stage.append(ring);

    if (mode === "kernel") {
      for (let index = 0; index < 3; index += 1) {
        const ray = document.createElement("span");
        ray.className = "kernel-ray";
        ray.style.setProperty("--angle", `${-index * 60}deg`);
        ray.style.setProperty("--ray-color", RAY_COLORS[index]);
        ray.setAttribute("aria-hidden", "true");
        stage.append(ray);
      }
    }

    if (mode === "stabilizer") {
      [0, 90].forEach((angle) => {
        const axis = document.createElement("span");
        axis.className = "stabilizer-axis";
        axis.style.setProperty("--angle", `${angle}deg`);
        axis.setAttribute("aria-hidden", "true");
        stage.append(axis);
      });
    }

    const center = document.createElement("span");
    center.className = "rosette-center";
    center.setAttribute("aria-hidden", "true");
    stage.append(center);
  }

  function addMotif(stage, operation, mode) {
    const radians = (operation.positionAngle * Math.PI) / 180;
    const radius = 35;
    const x = 50 + radius * Math.cos(radians);
    const y = 50 - radius * Math.sin(radians);

    const motif = document.createElement("span");
    motif.className = `motif is-${operation.color}`;
    motif.style.left = `${x}%`;
    motif.style.top = `${y}%`;
    motif.setAttribute("aria-hidden", "true");

    const glyph = document.createElement("span");
    glyph.className = "motif-glyph";
    const reflection = operation.reflected ? " scaleY(-1)" : "";
    glyph.style.transform = `rotate(${-operation.power * 60}deg)${reflection}`;
    glyph.textContent = "R";
    motif.append(glyph);

    if (mode !== "plain" && mode !== "kernel" && mode !== "stabilizer") {
      const label = document.createElement("span");
      label.className = "motif-label";
      label.textContent = operation.label;
      motif.append(label);
    }

    stage.append(motif);
  }

  document.querySelectorAll("[data-rosette]").forEach((stage) => {
    const mode = stage.dataset.rosette || "plain";
    addStructure(stage, mode);
    operationData().forEach((operation) => addMotif(stage, operation, mode));
  });
})();
