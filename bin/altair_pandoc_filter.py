#!/usr/bin/env python
"""Altair element format:

`altair_div` filter syntax:
```<div class=altair s3_path="test.json" static_path="png/bivariate_scatters.png" id="fig:pipeline2" width="500" height="20%">
can haz $ma^t_h$ again?
</div>
```

`altair_xml` filter syntax:
`<altair s3_path="test.json" static_path="png/bivariate_scatters.png" caption="$E = mc^2$" id="fig:pipeline3" width="300"/>`
"""
import string
import json
import random
import subprocess
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

from pandocfilters import (
    toJSONFilter,
    Image,
    RawInline,
    Div,
    Span,
    Plain,
    Para,
)

tooltip_div = """<div id="vg-tooltip-element" class="vg-tooltip" style="top: 33px;
left: 75px"></div>"""

script = """
<script type="text/javascript">
  var spec = "{s3_path}";
  vegaEmbed('#{div_id}', spec, {options}).then(function(result) {{
  }}).catch(console.error);
</script>""".format


def altair_xml(key, value, format, meta):
    # format: output format
    # meta, Dict[str, JSON]: extra options, e.g. bucket
    # E.g. meta["bibliography"] = {'t': 'MetaString', 'c': 'test'}
    POSSIBLE_PROPERTIES = ["width", "height"]

    if key == "RawInline":
        _, xml = value
        try:
            element = ET.fromstring(xml)
        except ParseError:
            return
        if element.tag == "altair":
            # Label
            reference = element.get("id") or ""
            # Caption
            if value[0] == "html":
                caption_str = element.get("caption") or ""
            elif value[0] == "xml":
                caption_str = element.text or element.get("caption") or ""
            else:
                assert 0
            caption = parse_str(caption_str)["blocks"][0]["c"]

            properties = [
                (k, element.get(k)) for k in POSSIBLE_PROPERTIES if k in element.keys()
            ]

            if format == "html":
                bucket = meta["bucket"]["c"]
                s3_path = f"https://{bucket}.s3.amazonaws.com/{element.get('s3_path')}"

                div_id = "".join(random.sample(string.ascii_letters, 5))
                div = f'<div id="{div_id}"></div>'

                options = dict(properties)
                options.setdefault("actions", False)

                return Span(
                    ("", [], properties),
                    [
                        RawInline(
                            "html",
                            div
                            + script(
                                div_id=div_id,
                                s3_path=s3_path,
                                options=json.dumps(options),
                            )
                            + tooltip_div,
                        ),
                        Image(  # TODO: hide alt image text
                            [reference, [], properties],
                            caption,
                            ["data:,", "fig:"],
                        ),
                    ],
                )

            else:
                # Image path
                figure_path = meta["figure_path"]["c"]
                path = f"{figure_path}/{element.get('static_path')}"

                return Image(
                    [reference, [], properties],
                    caption,
                    [path, "fig:"],
                )


def altair_div(key, value, format, meta):
    if key == "Div":
        div_meta = value[0]
        div_content = value[1]
        if "altair" in div_meta[1]:
            # Label
            reference = div_meta[0]
            # Caption
            caption = div_content
            # Properties
            properties = dict(div_meta[2])

            if format == "html":
                bucket = meta["bucket"]["c"]
                s3_path = f"https://{bucket}.s3.amazonaws.com/{properties['s3_path']}"

                div_id = "".join(random.sample(string.ascii_letters, 5))
                div = f'<div id="{div_id}"></div>'

                options = properties.copy()
                options.setdefault("actions", False)

                return Div(
                    ("", [], list(properties.items())),
                    [
                        Plain(
                            [
                                RawInline(
                                    "html",
                                    div
                                    + script(
                                        div_id=div_id,
                                        s3_path=s3_path,
                                        options=json.dumps(options),
                                    )
                                    # + tooltip_div,
                                ),
                            ]
                        ),
                        Para(
                            [  # Empty image serves sole purpose of caption + reference
                                Image(
                                    [
                                        reference,
                                        [],
                                        [
                                            ("onerror", "this.style.display='none'"),
                                        ],
                                    ],
                                    caption[0]["c"],
                                    [
                                        "data:,",
                                        "fig:",
                                    ],
                                ),
                            ]
                        ),
                    ],
                )

            else:
                # Image path
                figure_path = meta["figure_path"]["c"]
                path = f"{figure_path}/{properties['static_path']}"

                return Para(
                    [
                        Image(
                            [reference, [], list(properties.items())],
                            # [Str(str(caption[0]["c"]))],
                            caption[0]["c"],
                            [path, "fig:"],
                        )
                    ]
                )


def parse_str(s):
    """Run pandoc on `s` and output as JSON."""
    process = subprocess.run(
        ["pandoc", "-t", "json", "-f", "markdown"],
        input=s.encode(),
        capture_output=True,
        check=True,
    )
    return json.loads(process.stdout)


if __name__ == "__main__":
    toJSONFilter(altair_div)
