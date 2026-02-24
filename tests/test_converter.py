import sys
import types
import importlib
import os


def make_fake_epubcheck():
    mod = types.SimpleNamespace()

    class Result:
        def __init__(self, valid):
            self.valid = valid

    def EpubCheck(path):
        # mark files with 'bad' in the name as invalid
        return Result(valid=('bad' not in path))

    mod.EpubCheck = EpubCheck
    return mod


def reload_converter_with_fake_epubcheck(monkeypatch):
    if 'converter' in sys.modules:
        del sys.modules['converter']
    monkeypatch.setitem(sys.modules, 'epubcheck', make_fake_epubcheck())
    # Provide a harmless fake 'schedule' module so importing converter doesn't fail
    monkeypatch.setitem(sys.modules, 'schedule', types.SimpleNamespace())
    return importlib.import_module('converter')


def test_auto_fix_skips_when_backup_exists(monkeypatch, capsys):
    converter = reload_converter_with_fake_epubcheck(monkeypatch)

    # Simulate that the original backup already exists
    def fake_exists(path):
        return path.endswith('.original.epub')

    monkeypatch.setattr('os.path.exists', fake_exists)

    subprocess_called = {'called': False}

    def fake_run(cmd, check=True):
        subprocess_called['called'] = True

    monkeypatch.setattr('subprocess.run', fake_run)

    converter.auto_fix_epub('/books/Author/Book.epub')

    out = capsys.readouterr().out
    assert 'Skipping: Original backup already exists' in out
    assert subprocess_called['called'] is False


def test_run_integrity_check_skips_original_and_auto_fixes(monkeypatch, capsys):
    converter = reload_converter_with_fake_epubcheck(monkeypatch)

    # Provide a fake os.walk that yields one folder with a good.original.epub and bad.epub
    def fake_walk(path):
        yield ('/books/Author', [], ['good.original.epub', 'bad.epub'])

    monkeypatch.setattr('os.walk', fake_walk)

    # Ensure DRY_RUN is False so auto-fix would be attempted
    monkeypatch.setattr(converter, 'DRY_RUN', False)

    auto_fix_called = {'called': False, 'path': None}

    def fake_auto_fix(path):
        auto_fix_called['called'] = True
        auto_fix_called['path'] = path

    monkeypatch.setattr(converter, 'auto_fix_epub', fake_auto_fix)

    converter.run_integrity_check()

    out = capsys.readouterr().out
    assert 'Skipping: File appears to be an original/backup: good.original.epub' in out
    assert auto_fix_called['called'] is True
    assert auto_fix_called['path'].endswith('bad.epub')
