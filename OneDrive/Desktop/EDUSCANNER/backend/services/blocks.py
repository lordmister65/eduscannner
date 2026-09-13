BLOCK_QUESTION_COUNTS = {1:20, 2:30, 3:20, 4:30, 5:30, 6:30, 7:45, 8:45}

def question_count_for_block(block):
    if block not in BLOCK_QUESTION_COUNTS:
        raise ValueError("Bloco inválido")
    return BLOCK_QUESTION_COUNTS[block]
