
import os
from pathlib import Path
from time import sleep
from mutmut.cache import Mutant, MutantCollection, MutantIterator
from pytest import raises, fixture
from unittest.mock import MagicMock, patch

from mutmut import (
    AndOrTestMutationStrategy,
    ArgumentMutationStrategy,
    DecoratorMutationStrategy,
    ExpressionMutationStrategy,
    FstringMutationStrategy,
    KeywordMutationStrategy,
    LambdaMutationStrategy,
    NameMutationStrategy,
    OperatorMutationStrategy,
    NumberMutationStrategy,
    StringMutationStrategy,
    partition_node_list,
    run_mutation_tests,
    check_mutants,
    close_active_queues,
    read_patch_data,
    OK_KILLED,
    Context, 
    mutate)


def test_partition_node_list_no_nodes():
    with raises(AssertionError):
        partition_node_list([], None)


def test_name_mutation_simple_mutants():
    strategy = NameMutationStrategy()
    assert strategy.mutate(node=None, value='True') == 'False'


def test_context_exclude_line():
    source = "__import__('pkg_resources').declare_namespace(__name__)\n"
    assert mutate(Context(source=source)) == (source, 0)

    source = "__all__ = ['hi']\n"
    assert mutate(Context(source=source)) == (source, 0)


def check_mutants_stub(**kwargs):
    def run_mutation_stub(*_):
        sleep(0.15)
        return OK_KILLED
    check_mutants_original = check_mutants
    with patch('mutmut.run_mutation', run_mutation_stub):
        check_mutants_original(**kwargs)


class ConfigStub:
    hash_of_tests = None


config_stub = ConfigStub()


def test_run_mutation_tests_thread_synchronization(monkeypatch):
    # arrange
    total_mutants = 3
    cycle_process_after = 1

    def queue_mutants_stub(**kwargs):
        for _ in range(total_mutants):
            kwargs['mutants_queue'].put(('mutant', Context(config=config_stub)))
        kwargs['mutants_queue'].put(('end', None))
    monkeypatch.setattr('mutmut.queue_mutants', queue_mutants_stub)

    def update_mutant_status_stub(**_):
        sleep(0.1)

    monkeypatch.setattr('mutmut.check_mutants', check_mutants_stub)
    monkeypatch.setattr('mutmut.cache.update_mutant_status', update_mutant_status_stub)
    monkeypatch.setattr('mutmut.CYCLE_PROCESS_AFTER', cycle_process_after)

    progress_mock = MagicMock()
    progress_mock.registered_mutants = 0

    def progress_mock_register(*_):
        progress_mock.registered_mutants += 1
        
    progress_mock.register = progress_mock_register

    # act
    run_mutation_tests(config_stub, progress_mock, None)

    # assert
    assert progress_mock.registered_mutants == total_mutants

    close_active_queues()


@fixture
def testpatches_path(testdata: Path):
    return testdata / "test_patches"


def test_read_patch_data_new_empty_file_not_in_the_list(testpatches_path: Path):
    # arrange
    new_empty_file_name = "new_empty_file.txt"
    new_empty_file_patch = testpatches_path / "add_empty_file.patch"

    # act
    new_empty_file_changes = read_patch_data(new_empty_file_patch)

    # assert
    assert not new_empty_file_name in new_empty_file_changes


def test_read_patch_data_removed_empty_file_not_in_the_list(testpatches_path: Path):
    # arrange
    existing_empty_file_name = "existing_empty_file.txt"
    remove_empty_file_patch = testpatches_path / "remove_empty_file.patch"

    # act
    remove_empty_file_changes = read_patch_data(remove_empty_file_patch)

    # assert
    assert existing_empty_file_name not in remove_empty_file_changes


def test_read_patch_data_renamed_empty_file_not_in_the_list(testpatches_path: Path):
    # arrange
    renamed_empty_file_name = "renamed_existing_empty_file.txt"
    renamed_empty_file_patch = testpatches_path / "renamed_empty_file.patch"

    # act
    renamed_empty_file_changes = read_patch_data(renamed_empty_file_patch)

    # assert
    assert renamed_empty_file_name not in renamed_empty_file_changes


def test_read_patch_data_added_line_is_in_the_list(testpatches_path: Path):
    # arrange
    file_name = "existing_file.txt"
    file_patch = testpatches_path / "add_new_line.patch"

    # act
    file_changes = read_patch_data(file_patch)

    # assert
    assert file_name in file_changes
    assert file_changes[file_name] == {3} # line is added between second and third


def test_read_patch_data_edited_line_is_in_the_list(testpatches_path: Path):
    # arrange
    file_name = "existing_file.txt"
    file_patch = testpatches_path / "edit_existing_line.patch"

    # act
    file_changes = read_patch_data(file_patch)

    # assert
    assert file_name in file_changes
    assert file_changes[file_name] == {2} # line is added between 2nd and 3rd


def test_read_patch_data_edited_line_in_subfolder_is_in_the_list(testpatches_path: Path):
    # arrange
    file_name = os.path.join("sub", "existing_file.txt") # unix will use "/", windows "\" to join
    file_patch = testpatches_path / "edit_existing_line_in_subfolder.patch"

    # act
    file_changes = read_patch_data(file_patch)

    # assert
    assert file_name in file_changes
    assert file_changes[file_name] == {2} # line is added between 2nd and 3rd


def test_read_patch_data_renamed_file_edited_line_is_in_the_list(testpatches_path: Path):
    # arrange
    original_file_name = "existing_file.txt"
    new_file_name = "renamed_existing_file.txt"
    file_patch = testpatches_path / "edit_existing_renamed_file_line.patch"

    # act
    file_changes = read_patch_data(file_patch)

    # assert
    assert original_file_name not in file_changes
    assert new_file_name in file_changes
    assert file_changes[new_file_name] == {3} # 3rd line is edited


def test_read_patch_data_mutliple_files(testpatches_path: Path):
    # arrange
    expected_changes = {
        "existing_file.txt": {2, 3},
        "existing_file_2.txt": {4, 5},
        "new_file.txt": {1, 2, 3}
    }
    file_patch = testpatches_path / "multiple_files.patch"

    # act
    actual_changes = read_patch_data(file_patch)

    # assert
    assert actual_changes == expected_changes

# extension

# ---------------------- number -------------------------
def test_number_mutation_positive_integer():
    strategy = NumberMutationStrategy()
    result = strategy.mutate(node=None, value='42')
    assert result == '43'

# ---------------------- string -------------------------
def test_string_mutation_simple():
    strategy = StringMutationStrategy()
    result = strategy.mutate(node=None, value='"hello"')
    assert result == '"XXhelloXX"'

# ---------------------- keyword ------------------------
def test_keyword_mutation_is_to_is_not():
    strategy = KeywordMutationStrategy()

    # is --> is not
    context = MagicMock()
    context.stack = [MagicMock(), MagicMock()]
    context.stack[-2].type = 'comp_op'

    result = strategy.mutate(node=None, value='is', context=context)

    assert result == 'is not'

# ---------------------- operator -----------------------
def test_operator_mutation_plus_to_minus():
    strategy = OperatorMutationStrategy()

    context = MagicMock()
    # with None is not working
    node = MagicMock()

    result = strategy.mutate(node=node, value='+', context=context)

    assert result == '-'

# ---------------------- name ---------------------------
def test_name_mutation_true_to_false():
    strategy = NameMutationStrategy()

    context = MagicMock()
    node = MagicMock()
    value = 'True'

    result = strategy.mutate(node=node, value=value, context=context)

    assert result == 'False'


# ---------------------- andortest ----------------------
def test_and_to_or_mutation():
    strategy = AndOrTestMutationStrategy()

    # x and y --> x or y
    node = MagicMock()
    children = [
        MagicMock(type='name', value='x'),
        MagicMock(type='keyword', value='and'),
        MagicMock(type='name', value='y')
    ]

    result = strategy.mutate(node=node, children=children)

    assert result is not None
    # should have a space because of the mutation
    assert result[1].value == ' or'

def test_or_to_and_mutation():
    strategy = AndOrTestMutationStrategy()

    node = MagicMock()
    children = [
        MagicMock(type='name', value='x'),
        MagicMock(type='keyword', value='or'),
        MagicMock(type='name', value='y')
    ]

    result = strategy.mutate(node=node, children=children)

    assert result is not None
    assert result[1].value == ' and'

# ---------------------- lambda -------------------------
def test_lambda_with_returning_none():
    strategy = LambdaMutationStrategy()

    # x: None, lambda function
    node = MagicMock()
    children = [
        MagicMock(type='parameters', value='x'),
        MagicMock(type='operator', value=':'),
        MagicMock(type='name', value='None')
    ]

    result = strategy.mutate(node=node, value=':', children=children)

    assert result is not None
    # again the space
    assert result[-1].value == ' 0'

def test_lambda_with_returning_value():
    strategy = LambdaMutationStrategy()

    # x: 5
    node = MagicMock()
    children = [
        MagicMock(type='parameters', value='x'),
        MagicMock(type='operator', value=':'),
        MagicMock(type='name', value='5')
    ]

    result = strategy.mutate(node=node, value=':', children=children)

    assert result is not None
    # the space another time
    assert result[-1].value == ' None'

# expression
def test_expression_mutation_simple_assignment():
    strategy = ExpressionMutationStrategy()

    # x = 10
    node = MagicMock()
    children = [
        MagicMock(type='name', value='x'),
        MagicMock(type='operator', value='='),
        MagicMock(type='name', value='10')
    ]

    result = strategy.mutate(node=node, children=children)

    assert result is not None
    # last one None --> x = None
    assert result[-1].value == ' None'


# decorator
def test_decorator_mutation_single_decorator():
    strategy = DecoratorMutationStrategy()

    
    node = MagicMock()
    # decorator + newline (empty)    
    children = [
        MagicMock(type='decorator', value='@my_decorator'),
        MagicMock(type='newline', value='\n')
    ]

    result = strategy.mutate(node=node, children=children)

    assert result is not None
    # only one result (decorator deleted)
    assert len(result) == 1
    # the only node should be what was below decorator (newline)
    assert result[0].type == 'newline'

# iterator
def test_iterator ():
    # contexts for checking collection iterated == list of context
    context1 = Context()  
    context2 = Context()
    context3 = Context()
    
    mutations = [context1, context2, context3]  
    collection = MutantCollection(mutations)
    
    result = [mutant for mutant in collection]
    assert result == mutations
