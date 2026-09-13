from backend.services.blocks import BLOCK_QUESTION_COUNTS
def test_blocks():
    assert BLOCK_QUESTION_COUNTS == {1:20,2:30,3:20,4:30,5:30,6:30,7:45,8:45}
