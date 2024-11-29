application {
    this.mainClassName = mainVerticleName
}


named<JavaExec>("run") {
    doFirst {
        args = listOf(
            "run",
            mainVerticleName,
            "--launcher-class=${application.mainClassName}",
            "--on-redeploy=$doOnChange"
        )
    }
}
