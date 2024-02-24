import textchecker


def test_create_marked_html():
    text = "Text to check for sensitive terms like color and some more text like race"
    text_list = text.split(" ")
    indices = [7, 13]
    html = textchecker.create_marked_html(text_list, indices)
    assert html == "Text to check for sensitive terms like <mark>color</mark> and some more text like <mark>race</mark>"

    indices = [0, 7]
    html = textchecker.create_marked_html(text_list, indices)
    assert html == "<mark>Text</mark> to check for sensitive terms like <mark>color</mark> and some more text like race"

    indices = [0, 1, 4, 5, 13]
    html = textchecker.create_marked_html(text_list, indices)
    assert html == "<mark>Text to</mark> check for <mark>sensitive terms</mark> like color and some more text like <mark>race</mark>"