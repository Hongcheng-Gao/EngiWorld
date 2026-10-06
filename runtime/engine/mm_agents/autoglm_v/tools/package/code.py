import json
import os
import subprocess
from pathlib import Path


class CodeTools:
    ret = ""

    @classmethod
    def print_result(cls):
        """Print the execution result."""
        print(cls.ret)

    @classmethod
    def launch_vscode(cls, path):
        """
        Open a file or directory in an existing window.

        Args:
            path (str): File or directory path.
        """
        try:
            subprocess.run(["code", "-r", path], check=True)
            cls.ret = "Successfully launched VS Code"
        except subprocess.CalledProcessError as e:
            cls.ret = f"Error launching VS Code: {e}"
        except Exception as e:
            cls.ret = f"Unexpected error: {e}"

        return cls.ret

    @classmethod
    def env_info(cls):
        cls.ret = "None"

    @classmethod
    def compare_files(cls, file1, file2):
        """
        Compare two files in VS Code.

        Args:
            file1 (str): Path to the first file.
            file2 (str): Path to the second file.
        """
        try:
            # Get the comparison result.
            subprocess.run(["code", "-d", file1, file2], check=True)
            cls.ret = "The compared files are opened in VSCode"
        except subprocess.CalledProcessError as e:
            cls.ret = f"Error comparing files: {e}"
        except Exception as e:
            cls.ret = f"Unexpected error: {e}"

        return cls.ret

    @classmethod
    def add_folder(cls, folder):
        """
        Add a folder to the last active VS Code window.

        Args:
            folder (str): Folder path.
        """
        try:
            subprocess.run(["code", "-a", folder], check=True)
            cls.ret = "Successfully added folder"
        except subprocess.CalledProcessError as e:
            cls.ret = f"Error adding folder: {e}"
        except Exception as e:
            cls.ret = f"Unexpected error: {e}"

        return cls.ret

    @classmethod
    def goto_file(cls, file_path, line=1, character=1):
        """
        Open a file at a specific line and character position.

        Args:
            file_path (str): File path.
            line (int): Line number.
            character (int): Character position.
        """
        try:
            command = f"{file_path}:{line}:{character}"
            subprocess.run(["code", "-g", command], check=True)
            cls.ret = "Successfully opened file, line: {}, character: {}".format(line, character)
        except subprocess.CalledProcessError as e:
            cls.ret = f"Error going to file: {e}"
        except Exception as e:
            cls.ret = f"Unexpected error: {e}"

        return cls.ret

    @classmethod
    def perform_merge(cls, path1, path2, base, result):
        """
        Perform a three-way merge.

        Args:
            path1 (str): Path to the first version.
            path2 (str): Path to the second version.
            base (str): Path to the base version.
            result (str): Path for the merged result.
        """
        try:
            subprocess.run(["code", "-m", path1, path2, base, result], check=True)
            cls.ret = "Successfully performed merge"
        except subprocess.CalledProcessError as e:
            cls.ret = f"Error performing merge: {e}"
        except Exception as e:
            cls.ret = f"Unexpected error: {e}"

        return cls.ret

    @classmethod
    def remove_folder(cls, folder):
        """
        Remove a folder from the last active VS Code window.

        Args:
            folder (str): Folder path.
        """
        try:
            subprocess.run(["code", "--remove", folder], check=True)
            cls.ret = "Successfully removed folder"
        except subprocess.CalledProcessError as e:
            cls.ret = f"Error removing folder: {e}"
        except Exception as e:
            cls.ret = f"Unexpected error: {e}"

        return cls.ret

    @classmethod
    def install_extension(cls, extension_id, pre_release=False):
        """
        Install or update an extension in VS Code.

        Args:
            extension_id (str): Extension identifier.
            pre_release (bool): Whether to install a prerelease version.
        """
        try:
            command = ["code", "--install-extension", extension_id]
            if pre_release:
                command.append("--pre-release")
            subprocess.run(command, check=True)
            cls.ret = "Successfully installed extension"
        except subprocess.CalledProcessError as e:
            cls.ret = f"Error installing extension: {e}"
        except Exception as e:
            cls.ret = f"Unexpected error: {e}"

        return cls.ret

    @classmethod
    def uninstall_extension(cls, extension_id):
        """
        Uninstall a VS Code extension.

        Args:
            extension_id (str): Extension identifier.
        """
        try:
            subprocess.run(["code", "--uninstall-extension", extension_id], check=True)
            cls.ret = "Successfully uninstalled extension"
        except subprocess.CalledProcessError as e:
            cls.ret = f"Error uninstalling extension: {e}"
        except Exception as e:
            cls.ret = f"Unexpected error: {e}"

        return cls.ret

    @classmethod
    def list_extensions(cls, show_versions=False, category=None):
        """
        List installed VS Code extensions.

        Args:
            show_versions (bool): Whether to show extension versions.
            category (str): Filter extensions by category.
        """
        try:
            command = ["code", "--list-extensions"]
            if show_versions:
                command.append("--show-versions")
            if category:
                command.extend(["--category", category])
            cls.ret = subprocess.run(command, check=True, capture_output=True, text=True).stdout
        except subprocess.CalledProcessError as e:
            cls.ret = f"Error listing extensions: {e}"
        except Exception as e:
            cls.ret = f"Unexpected error: {e}"

        return cls.ret

    @classmethod
    def update_extensions(cls):
        """
        Update all installed VS Code extensions to their latest versions.
        """
        try:
            subprocess.run(["code", "--update-extensions"], check=True)
            cls.ret = "Successfully updated extensions"
        except subprocess.CalledProcessError as e:
            cls.ret = f"Error updating extensions: {e}"
        except Exception as e:
            cls.ret = f"Unexpected error: {e}"

        return cls.ret

    @classmethod
    def disable_extension(cls, extension_id):
        """
        Disable the specified extension in the next VS Code window.

        Args:
            extension_id (str): Extension identifier.
        """
        try:
            subprocess.run(["code", "--disable-extension", extension_id], check=True)
            cls.ret = "Successfully disabled extension"
        except subprocess.CalledProcessError as e:
            cls.ret = f"Error disabling extension: {e}"
        except Exception as e:
            cls.ret = f"Unexpected error: {e}"

        return cls.ret

    @classmethod
    def toggle_sync(cls, state):
        """
        Enable or disable synchronization in VS Code.

        Args:
            state (str): Use 'on' to enable or 'off' to disable.
        """
        try:
            command = ["code", "--sync", state]
            subprocess.run(command, check=True)
            cls.ret = "Successfully toggled sync"
        except subprocess.CalledProcessError as e:
            cls.ret = f"Error toggling sync: {e}"
        except Exception as e:
            cls.ret = f"Unexpected error: {e}"

        return cls.ret
