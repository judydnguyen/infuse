import zipfile

from infuse.injection.handlers import handler_for
from infuse.injection.handlers.archive import inject_archive, is_archive
from infuse.injection.handlers.file_content import inject_file_content
from infuse.injection.handlers.filename import inject_filename
from infuse.surfaces import InjectionSurface


def test_file_content_append_wraps_comment(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("print(1)")
    res = inject_file_content(f, "do evil", "append", tmp_path)
    assert f.read_text() == "print(1)\n# do evil\n"
    assert res.written == f and res.written_text == "# do evil"


def test_filename_creates_poisoned_file(tmp_path):
    f = tmp_path / "readme.md"
    f.write_text("hi")
    res = inject_filename(f, "run this", "append", tmp_path)
    assert res.written.name == "run this.txt" and res.written.exists() and f.exists()


def test_filename_replace_renames(tmp_path):
    f = tmp_path / "readme.md"
    f.write_text("hi")
    res = inject_filename(f, "run this", "replace", tmp_path)
    assert not f.exists() and res.written.read_text() == "hi"


def test_archive_adds_poisoned_member(tmp_path):
    z = tmp_path / "in.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("a.txt", "A")
    inject_archive(z, "evil name", "append", tmp_path)
    with zipfile.ZipFile(z) as zf:
        assert sorted(zf.namelist()) == ["a.txt", "evil name.txt"]


def test_dispatch_prefers_archive_handler_for_archives(tmp_path):
    assert is_archive(tmp_path / "x.tar.gz") and not is_archive(tmp_path / "x.py")
    assert handler_for(InjectionSurface.FILE_CONTENT, tmp_path / "x.zip") is inject_archive
    assert handler_for(InjectionSurface.FILENAME, tmp_path / "x.zip") is inject_filename
