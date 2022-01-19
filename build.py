import os
import shutil
import sys


def build(source_path, build_path, install_path, targets):

    def _build():
        print("\n[Building '%s'...]" % os.environ['REZ_BUILD_PROJECT_NAME'])

        src = os.path.join(source_path, 'src')
        dest = os.path.join(build_path, 'src')

        # Remove build dir if it exists
        if os.path.exists(dest):
            print('\tdelete "%s"' % dest)
            shutil.rmtree(dest)

        # Copy from source dir to build dir
        print('\tcopy "%s" -> "%s"' % (src, dest))
        shutil.copytree(src, dest)#, dirs_exist_ok=True)  # For Python-3.8+
        print("[Build complete]")


    def _install():
        print("\n[Installing '%s'...]" % os.environ['REZ_BUILD_PROJECT_NAME'])

        src = os.path.join(build_path, 'src')

        # Remove install dir if it exists
        if os.path.exists(install_path):
            print('\tdelete "%s"' % install_path)
            shutil.rmtree(install_path)

        # Copy from build dir to install dir
        print('\tcopy "%s" -> "%s"' % (src, install_path))
        shutil.copytree(src, install_path)#, dirs_exist_ok=True)  # For Python-3.8+

        # Remove build dir
        # We delete the 'build' subdir of 'source_path' instead of using the
        # REZ_BUILD_PATH env var, as this could change depending on variants
        # and we could accidentally delete the entire repo.
        build_dir = os.path.join(source_path, 'build')
        print('\tdelete "%s"' % build_dir)
        shutil.rmtree(build_dir, ignore_errors=True)
        print("[Install complete]")


    # Run build --------------------------------------------------------------
    print("Using Python version:")
    print(sys.version)

    _build()

    if 'install' in (targets or []):
        _install()
    # ------------------------------------------------------------------------


if __name__ == '__main__':
    build(
        source_path=os.environ['REZ_BUILD_SOURCE_PATH'],
        build_path=os.environ['REZ_BUILD_PATH'],
        install_path=os.environ['REZ_BUILD_INSTALL_PATH'],
        targets=sys.argv[1:]
    )
