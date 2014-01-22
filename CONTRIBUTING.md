Contributing Changes to 1flow
-----------------------------

Contributing to the project is both welcomed and encouraged. To do so, you have at least two options:

# Hacking the code directly

- Fork the project.
- Create a branch for your changes.
- Modify the files as appropriate.
- Make `flake8` happy on your modified files;
	- you can ignore `["E221", "E241", "E272"]`, I do.
	- Please, remove trailing spaces/tabs at the end of *any* line.
-  Update documentation (you can do it via the Django admin for a friendly-editing interface, it's the `Help contents` section) :
	- if you add/change any user-visible feature, update the “features” documentation in english, if not sure of your english, feel free to ask on the IRC channel.
		- If you are not english native, be kind enough to update the translated version in your native language.
		- eventually ping on IRC for other developpers, it's best if we can gather all translations before accepting the patch.
	- If you change anything related to the documented architecture, update it in the `docs/` folder.
- Add tests to the following files and follow their format/conventions:
    - `{base,core}/tests/test_*.py`
-  Obviously, make sure all tests pass. Sorry for having asked it. Just run `make test` and enjoy whatever pleases you.
- Push your branch to `GitHub` and submit a pull request,
- Wait for my neurons to connect.

# Or submitting issues / feedback

If you don't feel comfortable forking the project or modifying it, you can also [submit an issue](https://github.com/1flow/1flow/issues) that includes the appropriate request.

If you found a bug, please include anything that can help us reproduce it, **excluding any of your passwords**. Never give them to anybody. If we need to access some of your personal data for any reason, we will discuss it first, and ask for something like a read-only/partial-display screen-sharing with your approval.

Thanks!
