from unittest.mock import patch, MagicMock
from pathlib import Path
from flux.demos.feature_test import FeatureDemo

@patch('flux.demos.feature_test.Path.rglob')
def test_analyze_files(mock_rglob):
    mock_rglob.return_value = ['file1.py', 'file2.py', 'file3.py']
    demo = FeatureDemo(Path('/fake/dir'))
    result = demo.analyze_files()
    assert result == {'python_files': 3}

@patch('flux.demos.feature_test.subprocess.run')
def test_get_git_info(mock_run):
    mock_result = MagicMock()
    mock_result.stdout = 'commit1\ncommit2\ncommit3\ncommit4\ncommit5'
    mock_run.return_value = mock_result
    demo = FeatureDemo(Path('/fake/dir'))
    result = demo.get_git_info()
    assert result == {'git_log': 'commit1\ncommit2\ncommit3\ncommit4\ncommit5'}

@patch('flux.demos.feature_test.FeatureDemo.analyze_files')
@patch('flux.demos.feature_test.FeatureDemo.get_git_info')
def test_generate_summary(mock_get_git_info, mock_analyze_files):
    mock_analyze_files.return_value = {'python_files': 3}
    mock_get_git_info.return_value = {'git_log': 'commit1\ncommit2\ncommit3\ncommit4\ncommit5'}
    demo = FeatureDemo(Path('/fake/dir'))
    summary = demo.generate_summary()
    expected_summary = "Python Files: 3\nGit Info:\ncommit1\ncommit2\ncommit3\ncommit4\ncommit5"
    assert summary == expected_summary
