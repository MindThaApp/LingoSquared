// Metro config for the npm-workspaces monorepo this app lives in (root
// package.json's "workspaces" links frontend/, mobile/, and packages/*).
// Without this, Metro can't resolve @lingo/shared: node_modules/@lingo/shared
// is a symlink to ../../packages/shared, and Metro's default watchFolders is
// just this project directory -- it never sees files outside it, so a
// symlinked workspace package silently fails to resolve/hot-reload.
// See https://docs.expo.dev/guides/monorepos/.
const { getDefaultConfig } = require("expo/metro-config");
const path = require("path");

const projectRoot = __dirname;
const workspaceRoot = path.resolve(projectRoot, "..");

const config = getDefaultConfig(projectRoot);

// 1. Watch the whole monorepo, not just mobile/, so changes to
//    packages/shared/src/** trigger a Metro rebuild.
config.watchFolders = [workspaceRoot];

// 2. Resolve node_modules from both mobile/ and the hoisted workspace root.
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, "node_modules"),
  path.resolve(workspaceRoot, "node_modules"),
];

module.exports = config;
