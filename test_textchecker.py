import textchecker


def test_create_marked_html():
    text = "Text to check for sensitive terms like color and some more text like race"
    text_list = text.split(" ")
    indices = [7, 13]
    html = textchecker.create_marked_html(text_list, indices)
    assert html == "<span>Text to check for sensitive terms like</span><button class='style_sensitive_word_highlight'>color</button><span>and some more text like</span><button class='style_sensitive_word_highlight'>race</button>"

    indices = [0, 7]
    html = textchecker.create_marked_html(text_list, indices)
    assert html == "<button class='style_sensitive_word_highlight'>Text</button><span>to check for sensitive terms like</span><button class='style_sensitive_word_highlight'>color</button><span>and some more text like race</span>"

    indices = [0, 1, 4, 5, 13]
    html = textchecker.create_marked_html(text_list, indices)
    assert html == "<button class='style_sensitive_word_highlight'>Text to</button><span>check for</span><button class='style_sensitive_word_highlight'>sensitive terms</button><span>like color and some more text like</span><button class='style_sensitive_word_highlight'>race</button>"