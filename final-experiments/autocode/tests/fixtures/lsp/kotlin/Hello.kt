data class NameBox(val value: String)

interface Greeter {
    fun greet(name: NameBox): String
}

class LocalGreeter : Greeter {
    override fun greet(name: NameBox): String = "Hello, ${name.value}"
}

fun NameBox.shout(): String = value.uppercase()

fun runGreeter(greeter: Greeter): String {
    return greeter.greet(NameBox("AutoCode"))
}

fun broken(): Int {
    return "intentional type error"
}
