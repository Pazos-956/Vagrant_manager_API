from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("."))
template = env.get_template("vagrantfile.template")

info = { "cpu": "2", "mem": "2048", "boxname": "generic/rocky8"}

contenido = template.render()

file = open("Vagrantfile2", "w")
file.write(contenido)

