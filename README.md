# Dapr Installer Bundle

## Overview
Dapr Installer Bundle contains CLI, runtime and dashboard packaged together. This eliminates the need to download binaries as well as docker images when initializing Dapr locally, especially in airgap/offline environment. The bundle structure is fixed and is as follows:
```
daprbundle
├── dapr
├── dist
│   ├── daprd_<runtime_os>_<runtime_arch>.tar.gz (`.zip` for windows)
│   ├── dashboard_<runtime_os>_<runtime_arch>.tar.gz (`.zip` for windows)
│   ├── placement_<runtime_os>_<runtime_arch>.tar.gz (`.zip` for windows)
├── docker
│   ├── daprio/dapr-<runtime_ver>.tar.gz
└── details.json
```

`details.json` file contains the following contents in json format:
```
  {
    "daprd": <runtime_ver>,
    "dashboard": <dashboard_ver>,
    "cli": <cli_ver>,
    "daprBinarySubDir": <binaries_subdirectoryName>,
    "dockerImageSubDir": <images_subdirectoryName>,
    "daprImageName": <dapr_imageName>,
    "daprImageFileName": <dapr_imageFileName>
  }
```

> Note: `details.json` file has been set with Read-Only permissions (0444) by default. It is advised to not modify it's contents, which may lead to undefined behavior during Dapr initialization.

## Setup
Each release of Dapr Installer Bundle includes various OSes and architectures. These packages can be manually downloaded and used to initialize dapr locally.

1.  Download the [Dapr Installer Bundle](https://github.com/dapr/installer-bundle/releases) for the specific release version. For example, daprbundle_linux_amd64.tar.gz, daprbundle_windows_amd64.zip.
2. Unpack it.
3. To install Dapr CLI copy the `daprbundle/dapr (dapr.exe for Windows)` binary to the desired location:
   * For Linux/MacOS - `/usr/local/bin`
   * For Windows, create a directory and add this to your System PATH. For example create a directory called `c:\dapr` and add this directory to your path, by editing your system environment variable.

   > Note: If Dapr CLI is not moved to the desired location, you can use local `dapr` CLI binary in the bundle. The steps above is to move it to the usual location and add it to the path.

### Install Dapr on your local machine (self-hosted)

In self-hosted mode, dapr can be initialized using the CLI  with the placement container enabled by default(recommended) or without it(slim installation) which also does not require docker to be available in the environment.

#### Initialize Dapr

([Prerequisite](#Prerequisites): Docker is available in the environment - recommended)

Use the init command to initialize Dapr. On init, multiple default configuration files and containers are installed along with the dapr runtime binary. Dapr runtime binary is installed under $HOME/.dapr/bin for Mac, Linux and %USERPROFILE%\.dapr\bin for Windows.

Move to the bundle directory and run the following command:
``` bash
dapr init --from-dir .
```
> For linux users, if you run your docker cmds with sudo, you need to use "**sudo dapr init**" 

> If you are not running the above cmd from the bundle directory, provide the full path to bundle directory as input. e.g. assuming bundle directory path is $HOME/daprbundle, run `dapr init --from-dir $HOME/daprbundle` to have the same behavior.


Output should look like as follows:
```bash
  Making the jump to hyperspace...
ℹ️  Installing runtime version latest
↘  Extracting binaries and setting up components... Loaded image: daprio/dapr:$version
✅  Extracting binaries and setting up components...
✅  Extracted binaries and completed components set up.
ℹ️  daprd binary has been installed to $HOME/.dapr/bin.
ℹ️  dapr_placement container is running.
ℹ️  Use `docker ps` to check running containers.
✅  Success! Dapr is up and running. To get started, go here: https://aka.ms/dapr-getting-started
```
> Note: To see that Dapr has been installed successfully, from a command prompt run the `docker ps` command and check that the `daprio/dapr:$version` container is up and running.

This step creates the following defaults:

1. components folder which is later used during `dapr run` unless the `--components-path` option is provided. For Linux/MacOS, the default components folder path is `$HOME/.dapr/components` and for Windows it is `%USERPROFILE%\.dapr\components`.
2. component files in the components folder called `pubsub.yaml` and `statestore.yaml`.
3. default config file `$HOME/.dapr/config.yaml` for Linux/MacOS or for Windows at `%USERPROFILE%\.dapr\config.yaml` to enable tracing on `dapr init` call. Can be overridden with the `--config` flag on `dapr run`.

> Note: To emulate *online* dapr initialization using `dapr init`, you can also run redis/zipkin containers as follows:
```
1. docker run --name "dapr_zipkin" --restart always -d -p 9411:9411 openzipkin/zipkin
2. docker run --name "dapr_redis" --restart always -d -p 6379:6379 redislabs/rejson
```

#### Slim Init
Alternatively to the above, to have the CLI not install any default configuration files or run Docker containers, use the `--slim` flag with the init command. Only Dapr binaries will be installed.

``` bash
dapr init --slim --from-dir .
```

Output should look like this:
```bash
⌛  Making the jump to hyperspace...
ℹ️  Installing runtime version latest
↙  Extracting binaries and setting up components... 
✅  Extracting binaries and setting up components...
✅  Extracted binaries and completed components set up.
ℹ️  daprd binary has been installed to $HOME.dapr/bin.
ℹ️  placement binary has been installed to $HOME/.dapr/bin.
✅  Success! Dapr is up and running. To get started, go here: https://aka.ms/dapr-getting-started
```

>Note: When initializing Dapr with the `--slim` flag only the Dapr runtime binary and the placement service binary are installed. An empty default components folder is created with no default configuration files. During `dapr run` user should use `--components-path` to point to a components directory with custom configurations files or alternatively place these files in the default directory. For Linux/MacOS, the default components directory path is `$HOME/.dapr/components` and for Windows it is `%USERPROFILE%\.dapr\components`.

