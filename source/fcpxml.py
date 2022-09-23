from typing import Optional
from xml.etree.ElementTree import ElementTree, Element, parse as ParseXML
from copy import deepcopy
from pathlib import Path


class XMLHandler:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.tree: Optional[ElementTree] = None
        self.root: Optional[Element] = None

    def fix_xml_file(self) -> None:
        self.tree = ParseXML(self.path)
        self.root = self.tree.getroot()
        self.fix_xml()
        self.tree.write(self.path)

    def fix_xml(self) -> None:
        """A method to 'fix' the provided FCPXML tree so that Resolve will recognise it as a timeline.
        Usually involves adding some form of 'sequence' element."""
        pass


class SubclipHandler(XMLHandler):
    sequence_extraneous = ("uuid", "masterclipid", "ismasterclip", "in", "out")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.clip: Optional[Element] = None
        self.sequence: Optional[Element] = None
        self.video_media: Optional[Element] = None
        self.audio_media: Optional[Element] = None

        self.masterclipid: Optional[str] = None
        self.in_frame: Optional[int] = None
        self.out_frame: Optional[int] = None
        self.video_format: Optional[Element] = None
        self.audio_format: Optional[Element] = None

    def fix_xml(self):
        self.duplicate_and_rename_clip_block()
        self.record_extraneous()
        self.remove_extraneous_blocks()
        self.fix_media()

    def duplicate_and_rename_clip_block(self):
        self.clip = self.root.find("clip")
        self.sequence = deepcopy(self.clip)
        self.sequence.tag = "sequence"
        self.sequence.set("id", self.sequence.get("id").replace("clip", "seq"))
        self.root.append(self.sequence)

    def record_extraneous(self):
        self.masterclipid = self.clip.get("id")
        self.in_frame = int(self.clip.find("in").text)
        self.out_frame = int(self.clip.find("out").text)

    def remove_extraneous_blocks(self):
        for remove_block_tag in self.sequence_extraneous:
            self.sequence.remove(self.sequence.find(remove_block_tag))

    def find_media_formats(self):
        clipitem = self.clip.find("media").find("movie").findall("track")[0].findall("clipitem")[0]
        format_data = clipitem.find("./file/media")
        self.video_format = format_data.find("./movie/samplecharacteristics")
        self.audio_format = format_data.find("./audio/samplecharacteristics")

    def fix_media(self):
        media_element = self.sequence.find("media")
        self.find_media_formats()
        self.video_media = media_element.find("movie")
        self.audio_media = media_element.find("audio")
        self.fix_media_type(self.video_media, self.video_format)
        self.fix_media_type(self.audio_media, self.audio_format)

    def fix_media_type(self, media_element: Element, media_format: Element):
        format_element = Element("format", {})
        media_element.insert(0, format_element)
        format_element.append(deepcopy(media_format))

        for track in media_element.findall("track"):
            self.fix_media_track(track)

    def fix_media_track(self, track: Element):
        enabled_element = Element("enabled", {})
        enabled_element.text = "true"
        track.insert(0, enabled_element)

        for clipitem in track.findall("clipitem"):
            self.fix_media_clipitem(clipitem)

    def fix_media_clipitem(self, clipitem: Element):
        clipitem.set("id", f"seq-{clipitem.get('id')}")

        start = Element("start", {})
        start.text = str(self.in_frame)
        clipitem.insert(1, start)

        end = Element("end", {})
        end.text = str(self.out_frame)
        clipitem.insert(2, end)

        file = clipitem.find("file")
        file_id = file.get("id")
        file.clear()
        file.set("id", file_id)

        in_frame = Element("in", {})
        in_frame.text = str(self.in_frame)
        clipitem.insert(7, in_frame)

        out_frame = Element("out", {})
        out_frame.text = str(self.out_frame)
        clipitem.insert(8, out_frame)

        masterclipid = Element("masterclipid", {})
        masterclipid.text = self.masterclipid
        clipitem.insert(9, masterclipid)

