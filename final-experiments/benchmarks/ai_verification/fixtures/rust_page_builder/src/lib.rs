/// A minimal HTML page builder.
pub struct Page {
    title: String,
    body_items: Vec<String>,
}

impl Page {
    pub fn new(title: &str) -> Self {
        Page {
            title: title.to_string(),
            body_items: Vec::new(),
        }
    }

    pub fn add_paragraph(&mut self, text: &str) -> &mut Self {
        self.body_items.push(format!("<p>{}</p>", text));
        self
    }

    pub fn render(&self) -> String {
        format!(
            "<!DOCTYPE html><html><head><title>{title}</title></head><body>{body}</body></html>",
            title = self.title,
            body = self.body_items.join(""),
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_render_title() {
        let p = Page::new("Hello");
        assert!(p.render().contains("<title>Hello</title>"));
    }

    #[test]
    fn test_render_empty_body() {
        let p = Page::new("Empty");
        assert!(p.render().contains("<body></body>"));
    }

    #[test]
    fn test_render_paragraph() {
        let mut p = Page::new("Test");
        p.add_paragraph("world");
        assert!(p.render().contains("<p>world</p>"));
    }
}
