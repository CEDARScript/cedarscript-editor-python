application {
    mainClass.set(mainVerticleName)
}


named<JavaExec>("run") {
    doFirst {
        args = listOf(
            "run",
            mainVerticleName,
            "--launcher-class=${application.mainClass.get()}",
            "--on-redeploy=$doOnChange"
        )
    }
}
