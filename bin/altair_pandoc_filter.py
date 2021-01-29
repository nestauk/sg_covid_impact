#!/usr/bin/env python
"""Altair element format:
 `<altair s3_path="s3://.../spec.json"
  static_path="../../figures/path/to/image.png"/>`

TODO: Pass through width/reference information etc.
"""
import string
import random
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

from pandocfilters import toJSONFilter, Image, RawInline

tooltip_div = """<div id="vg-tooltip-element" class="vg-tooltip" style="top: 33px;
left: 75px"></div>"""

script = """
<script type="text/javascript">
  var spec = "{s3_path}";
  vegaEmbed('#{div_id}', spec, {{"actions": false}}).then(function(result) {{
    // Access the Vega view instance (https://vega.github.io/vega/docs/api/view/) as result.view
  }}).catch(console.error);
</script>""".format


def altair(key, value, format, meta):
    # format: output format
    # meta, Dict[str, JSON]: extra options, e.g. bucket
    # E.g. meta["bibliography"] = {'t': 'MetaString', 'c': 'test'}

    if key == "RawInline" and value[0] == "html":
        _, xml = value
        try:
            element = ET.fromstring(xml)
        except ParseError:
            return
        if element.tag == "altair":
            if format == "html":
                bucket = meta["bucket"]["c"]
                s3_path = f"https://{bucket}.s3.amazonaws.com/{element.get('s3_path')}"
                # s3_path = element.get('s3_path')

                div_id = "".join(random.sample(string.ascii_letters, 5))
                div = f'<div id="{div_id}"></div>'

                return RawInline(
                    "html", div + script(div_id=div_id, s3_path=s3_path) + tooltip_div
                )

            else:
                figure_path = meta["figure_path"]["c"]
                path = f"{figure_path}/{element.get('static_path')}"
                return Image(["", [], []], [], [path, "fig:"])


if __name__ == "__main__":
    toJSONFilter(altair)
