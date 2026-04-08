## Contributing

To ensure a smooth development environment, please adhere to the following rules for development:

1. Any time you notice an issue or think of a feature you want to implement, create an issue in GitHub. Give a detailed description of the issue/feature.

2. Everything is a branch. No code changes should be made on the main branch. Anytime you want to modify the code, use `git checkout -b [your-branch-name]`, make your changes there, then commit and merge.

To commit your code to Git, do the following:

1. `git status` to see all modified files.

2. `git add .` to add all modifications OR add files manually with `git add [your-file-name]`.

3. `git commit -m "[your-commit-message]"` to commit the changes to Git.

Then, when your code committed to your branch and ready to be merged, perform the following process:

1. `git checkout [your-branch-name]`

2. `git pull origin main`

3. `git push -u origin [your-branch-name]`

4. Open GitHub and find the "Compare & Pull Request" button at the top of the "Code" page.

5. Describe the code being merged and add something like `Resolves #12` where "#12" is the number of the issue that was opened in GitHub. Delete your branch from the GitHub repo after this is done (the option will appear).
