"""Audited short colour signatures from *The Symmetries of Things*.

The keys are Chaim Goodman--Strauss colour types.  Values are the first
printed short signature when the table gives equivalent alternatives.  A
caret introduces a non-numeric permutation superscript; Unicode raised
digits are used for the ordinary order labels.
"""

from __future__ import annotations


TWO_FOLD_SHORT_SIGNATURE_BY_TYPE: dict[str, str] = {
    "◦/◦": "◦¹,²",
    "2222/◦": "²2²2²2²2",
    "2222/2222": "¹2¹2²2²2",
    "**/××": "²*²*²",
    "**/*×": "²*¹*²",
    "**/** (1)": "²*¹*¹",
    "**/◦": "¹*²*²",
    "**/** (2)": "¹*¹*²",
    "××/◦": "×²×²",
    "××/××": "×¹×²",
    "*×/◦": "*²×²",
    "*×/××": "*²×¹",
    "*×/**": "*¹×²",
    "*2222/*2222": "*¹2¹2¹2²2",
    "*2222/**": "*¹2²2¹2²2",
    "*2222/2*22": "*¹2¹2²2²2",
    "*2222/22*": "*¹2²2²2²2",
    "*2222/2222": "*²2²2²2²2",
    "22*/22*": "¹2²2*¹",
    "22*/××": "²2²2*²",
    "22*/22×": "¹2²2*²",
    "22*/**": "²2²2*¹",
    "22*/2222": "¹2¹2*²",
    "22×/××": "²2²2×¹",
    "22×/2222": "¹2¹2×²",
    "2*22/22×": "²2*²2²2",
    "2*22/*×": "²2*¹2²2",
    "2*22/22*": "¹2*¹2²2",
    "2*22/2222": "¹2*²2²2",
    "2*22/*2222": "²2*¹2¹2",
    "442/442": "¹4²4²2",
    "442/2222": "²4²4¹2",
    "*442/4*2": "*¹4²4²2",
    "*442/442": "*²4²4²2",
    "*442/2*22": "*²4¹4²2",
    "*442/*2222": "*¹4²4¹2",
    "*442/*442": "*¹4¹4²2",
    "4*2/442": "¹4*²2",
    "4*2/2*22": "²4*¹2",
    "4*2/22×": "²4*²2",
    "*333/333": "*²3²3²3",
    "3*3/333": "¹3*²3",
    "632/333": "²6¹3²2",
    "*632/3*3": "*¹6²3²2",
    "*632/*333": "*²6¹3¹2",
    "*632/632": "*²6²3²2",
}

THREE_FOLD_SHORT_SIGNATURE_BY_TYPE: dict[str, str] = {
    "◦³/◦": "◦¹,³",
    "2222³//◦": "²2²2²2²2",
    "**³//◦": "¹*²*²",
    "**³/**": "³*¹*¹",
    "××³/××": "×³×³",
    "××³//◦": "×²×²",
    "*×³/*×": "*¹×³",
    "*×³//◦": "*²×²",
    "*2222³//**": "*¹2²2¹2²2",
    # ToS Table 12.1 and its official erratum print the intransitive
    # ¹2¹2*² action and kernel ◦.  The transitive S3 class has α and β
    # equal transpositions and P a distinct transposition, forcing this
    # signature and kernel ××.
    "22*³//××": "²2²2*²",
    "22*³//**": "²2²2*¹",
    "22×³//××": "²2²2×²",
    # Table 12.1 prints K=**, but the displayed S3 presentation fixes the
    # centred-mirror subgroup *×.  The short action signature itself is sound.
    "2*22³//*×": "²2*¹2²2",
    "333³/◦": "³3³3³3",
    "333³/333": "³3³3¹3",
    # Orders alone do not distinguish these two S3 actions.  Table 12.1
    # therefore retains the actual transpositions in the short signature.
    "*333³//◦": "*^(AB)3^(BC)3^(CA)3",
    "*333³//333": "*^(AB)3^(BC)3^(BC)3",
    # The two K labels in ToS Table 12.1 are inconsistent with the displayed
    # presentation.  The S3 action has torsion-free kernel ◦; the C3 action
    # has kernel *333.
    "3*3³//◦": "³3*²3",
    "3*3³/*333": "³3*¹3",
    # Table 12.1 misprints ³6²3²2; the derivation on p. 157 and Table 13.1
    # give the corrected regular C3 signature used by the clockwork atlas.
    "632³/2222": "³6³3¹2",
    # Table 12.1 leaves this cell blank; its S3 action and kernel force this
    # signature (6 -> transposition, 3 -> 3-cycle, 2 -> transposition).
    "632³//333": "²6³3²2",
    "*632³//2222": "*²6²3²2",
    "*632³//*333": "*¹6²3²2",
}
