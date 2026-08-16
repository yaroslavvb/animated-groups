(() => {
  "use strict";

  const COLORS = ["blue", "red", "green"];
  const RAY_COLORS = ["var(--blue)", "var(--red)", "var(--green)"];
  const PAIR_OFFSET_DEGREES = 15;
  function dadLabel(base, coset) {
    if (coset === 0) return base;
    return `${base} ${coset === 1 ? "r₆" : "r₃"}`;
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
          label: dadLabel("e", coset),
          positionAngle: baseAngle + PAIR_OFFSET_DEGREES,
        },
        {
          color: COLORS[coset],
          power: coset,
          reflected: true,
          label: dadLabel("Rₓ", coset),
          positionAngle: baseAngle - PAIR_OFFSET_DEGREES,
        },
        {
          color: COLORS[coset],
          power: oppositePower,
          reflected: false,
          label: dadLabel("r₂", coset),
          positionAngle: baseAngle + 180 + PAIR_OFFSET_DEGREES,
        },
        {
          color: COLORS[coset],
          power: oppositePower,
          reflected: true,
          label: dadLabel("Rᵧ", coset),
          positionAngle: baseAngle + 180 - PAIR_OFFSET_DEGREES,
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

  function motifColour(operation, mode) {
    if (mode === "catalogue-one") return "mono";
    if (mode === "catalogue-two-rotation") return operation.reflected ? "red" : "blue";
    if (mode === "catalogue-two-dihedral") return operation.power % 2 === 0 ? "blue" : "red";
    return operation.color;
  }

  function addMotif(stage, operation, mode) {
    const radians = (operation.positionAngle * Math.PI) / 180;
    const radius = 35;
    const x = 50 + radius * Math.cos(radians);
    const y = 50 - radius * Math.sin(radians);

    const motif = document.createElement("span");
    motif.className = `motif is-${motifColour(operation, mode)}`;
    motif.style.left = `${x}%`;
    motif.style.top = `${y}%`;
    motif.setAttribute("aria-hidden", "true");

    const glyph = document.createElement("span");
    glyph.className = "motif-glyph";
    const reflection = operation.reflected ? " scaleY(-1)" : "";
    glyph.style.transform = `rotate(${-operation.power * 60}deg)${reflection}`;
    glyph.textContent = "R";
    motif.append(glyph);

    if (mode === "colored") {
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
