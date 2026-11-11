// No GI dependencies: lifecycle invariants are also tested with fake themes.
export function unloadStylesheet(previousTheme, currentTheme, file) {
    if (!file) return;
    // Main.loadTheme() copies extension stylesheets before replacing the theme.
    // Remove that inherited entry as well as the previous theme's copy.
    currentTheme?.unload_stylesheet(file);
    if (previousTheme && previousTheme !== currentTheme)
        previousTheme.unload_stylesheet(file);
}

export function replaceStylesheet(previousTheme, currentTheme, previousFile, nextFile) {
    if (previousFile && previousFile.equal(nextFile))
        throw new Error('Runtime stylesheet revisions must use different file URIs');
    // Validate/load the replacement before removing a working stylesheet.
    // A unique URI avoids collisions in St.Theme's file-to-stylesheet tables.
    currentTheme.load_stylesheet(nextFile);
    unloadStylesheet(previousTheme, currentTheme, previousFile);
}
