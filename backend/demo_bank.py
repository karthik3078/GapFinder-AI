"""Curated offline fixtures; admitted only when their exact evidence is retrieved.

No precomputed student attempts or scores are seeded.
"""


def pair(prompt, options, quote, short, answer, rubric):
    return [
        {'kind': 'mcq', 'prompt': prompt, 'options': options, 'answer_index': 0,
         'reference_answer': options[0], 'explanation': quote, 'rubric': [options[0]], 'quote': quote},
        {'kind': 'short', 'prompt': short, 'options': [], 'answer_index': None,
         'reference_answer': answer, 'explanation': quote, 'rubric': rubric, 'quote': quote},
        {'kind': 'short', 'prompt': 'Give a brief explanation: ' + short, 'options': [], 'answer_index': None,
         'reference_answer': answer, 'explanation': quote, 'rubric': rubric, 'quote': quote},
    ]


BANK = {
    'Cell structure': pair('Which organelle stores genetic information?', ['Nucleus', 'Cell membrane', 'Vacuole', 'Cell wall'],
        'The nucleus stores genetic information and controls many cell activities.',
        'State two functions of the nucleus.', 'It stores genetic information and controls cell activities.', ['genetic information', 'controls cell activities']),
    'Membrane transport': pair('Which process requires ATP to move substances against a concentration gradient?', ['Active transport', 'Diffusion', 'Osmosis', 'Passive movement'],
        'Active transport moves substances against a concentration gradient and requires energy from ATP.',
        'Explain why active transport differs from diffusion.', 'Active transport moves against a concentration gradient and requires energy from ATP.', ['against concentration gradient', 'energy ATP']),
    'Photosynthesis': pair('Which pair of substances is consumed during photosynthesis?', ['Carbon dioxide and water', 'Glucose and oxygen', 'Glucose and carbon dioxide', 'Oxygen and water'],
        'Photosynthesis uses light energy to convert carbon dioxide and water into glucose and oxygen.',
        'Describe the inputs, energy source and outputs of photosynthesis.', 'Light energy converts carbon dioxide and water into glucose and oxygen.', ['light energy', 'carbon dioxide water', 'glucose oxygen']),
    'Respiration': pair('Which substance receives energy released during aerobic respiration?', ['ATP', 'Cellulose', 'Chlorophyll', 'DNA'],
        'Aerobic respiration breaks down glucose using oxygen and releases energy that is transferred to ATP.',
        'Explain how aerobic respiration supplies energy to a cell.', 'Glucose is broken down using oxygen and energy is transferred to ATP.', ['glucose oxygen', 'energy ATP']),
    'DNA and genes': pair('What is a gene?', ['A section of DNA coding for a functional product', 'An entire cell', 'A type of membrane', 'An energy molecule'],
        'A gene is a section of DNA that codes for a functional product, often a protein.',
        'Describe the relationship between a gene, DNA and a protein.', 'A gene is a section of DNA coding for a functional product, often a protein.', ['section DNA', 'codes functional product', 'protein']),
    'Mendelian inheritance': pair('What is the expected phenotype ratio from Aa crossed with Aa under complete dominance?', ['3 dominant to 1 recessive', '1 dominant to 3 recessive', '1 dominant to 1 recessive', 'All recessive'],
        'Under complete dominance, the expected phenotype ratio is 3 dominant to 1 recessive.',
        'Give the expected phenotype ratio for Aa crossed with Aa and state the dominance assumption.', '3 dominant to 1 recessive under complete dominance.', ['dominant recessive', 'complete dominance']),
}
