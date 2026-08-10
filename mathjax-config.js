window.MathJax = {
  tex: {
    inlineMath: [['\\(', '\\)']],
    displayMath: [['\\[', '\\]']],
    processEscapes: true,
    macros: {
      ST: [
        '#1\\;\\mathopen{\\lbrack\\!\\lbrack}\\,#2\\,\\mathclose{\\rbrack\\!\\rbrack}',
        2
      ]
    }
  },
  output: {
    displayOverflow: 'linebreak',
    linebreaks: {
      inline: true,
      width: '100%',
      lineleading: 0.2
    }
  },
  startup: {
    elements: ['.introduction', '#ke-wu', '.symmetry-list']
  }
};
