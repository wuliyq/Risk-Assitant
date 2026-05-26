# Risk-Management-Bot

# npm: Initialize a new project
## First-time Setup
If you've just installed `npm`, it'll save you some time later if you set some defaults in your config:

1. Set your name

    ```
    $ npm config set init-author-name "your name"
    ```

2. **Optional**: Set your preferred license type (default is [ISC](https://opensource.org/licenses/ISC)):

    ```
    $ npm config set init-license "MIT"
    ```
3. Add the following to a `.gitignore` file in the root of your project:

    ```
    node_modules
    npm-debug.log
    ```

    - One of the advantages of using npm is that we don't need to commit dependencies to our projects. Instead we `git pull` and then `npm install`.

## Instructions
1. Download or clone this project into your workspace;
3. Initialize an `npm` project by creating a `package.json` file:

    ```
    $ npm init
    ```

    - You will be asked to confirm the details of your project. 
    - See [Anatomy of a package.json file](https://www.digitalocean.com/community/tutorials/nodejs-package-json) for more details.
    - You can skip these questions with the `-y` flag:

        ```
        $ npm init -y
        ```
        
4. Once complete, you should have a new `package.json` file in your project directory.
5. Install your first package!

    ```
    $ npm install <project-name>
    ```

    - Search: "[Best npm packages for developers](https://www.google.com/search?q=Best+npm+packages+for+developers)"

