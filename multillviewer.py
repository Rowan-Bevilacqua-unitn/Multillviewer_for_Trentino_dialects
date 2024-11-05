import os
import sys
import xml.sax
import PySimpleGUI as sg
import platform
if platform.uname()[0] == "Windows":
    # Windows only, to address blurry fonts
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
#elif platform.uname()[0] == "Linux":
#    name = "linux.so"
import textwrap

class SaxHandler(xml.sax.ContentHandler):
    def startDocument(self):
        pass

    def startElement(self, name, attrs):
        global langName, langCode, langDescription, langPublisher, langProv, lemmas, senses, synsets
        self.inDefinition = False
        
        if name == "Lexicon":
            langName.append( attrs.getValue("label"))
            langCode.append( attrs.getValue("language"))
            langDescription.append( attrs.getValue("dc:description"))
            langPublisher.append( attrs.getValue("dc:publisher"))
            langProv.append( attrs.getValue("dc:source").split("; "))
        elif name == "Lemma":
            self.currentLemma = attrs.getValue("writtenForm") 
            self.currentLemmaPos = attrs.getValue("partOfSpeech")
        elif name == "Sense":
            self.currentSense = attrs.getValue("id")
            word = {}
            word["senseId"] = self.currentSense
            word["synsetId"] = attrs.getValue("synset")
            word["pos"] = self.currentLemmaPos
            if self.currentLemma not in lemmas:
                lemmas[self.currentLemma] = []
            lemmas[self.currentLemma].append(word)
            sense = {}
            sense["word"] = self.currentLemma
            sense["pos"] = self.currentLemmaPos
            sense["synsetId"] = word["synsetId"]
            if word["senseId"] not in senses:
                senses[word["senseId"]] = sense
            else:
                senses[word["senseId"]]["word"] = sense["word"]
                senses[word["senseId"]]["pos"] = sense["pos"]
                senses[word["senseId"]]["synsetId"] = sense["synsetId"]
            if sense["synsetId"] not in synsets:
                synsets[sense["synsetId"]] = {}
                synsets[sense["synsetId"]]["lemmas"] = []
            synsets[sense["synsetId"]]["lemmas"].append(self.currentLemma)

            if word["synsetId"] not in synsets:
                synsets[word["synsetId"]]={}
            if "senses" not in synsets[word["synsetId"]]:
                synsets[word["synsetId"]]["senses"]=[]
            synsets[word["synsetId"]]["senses"].append(word["senseId"])

        elif name == "Synset":
            synset = {}
            synset["ili"] = attrs.getValue("ili")
            synset["lexicalized"] = attrs.getValue("lexicalized")
            
            synsetId = attrs.getValue("id")

            if synset["ili"][-1] != 'n' and synset["ili"][-1] !='v' and synset["ili"][-1] !='a' and synset["ili"][-1] !='r':
                if synset["ili"] in synsets:
                    synsets[synset["ili"]][langCode[len(langCode)-1]]=synsetId

            self.currentSynset = synsetId
            if synset["lexicalized"]=="true":
                synset["pos"] = attrs.getValue("partOfSpeech")
            if synsetId not in synsets:
                synsets[synsetId] = synset
            else:
                synsets[synsetId]["ili"] = synset["ili"]
                synsets[synsetId]["lexicalized"] = synset["lexicalized"]
                synsets[synsetId]["pos"] = synset["pos"]
        elif name == "Definition":
            synsets[self.currentSynset]["gloss"] = "[" + attrs.getValue("language") + "] "
            self.inDefinition = True
            # will add actuall gloss when we get to the PCDATA
        elif name == "SenseRelation":
            reltype = attrs.getValue("relType")
            target = attrs.getValue("target")
            if "relations" not in senses[self.currentSense]:
                senses[self.currentSense]["relations"] = {}
            if reltype not in senses[self.currentSense]["relations"]:
                senses[self.currentSense]["relations"][reltype] = []
            senses[self.currentSense]["relations"][reltype].append(target)
            # now add the inverse relation if applicable
            if reltype in inverseRelations:
                inverseSource = target
                inverseTarget = self.currentSense
                inverseReltype = inverseRelations[reltype]
                if inverseSource not in senses:
                    senses[inverseSource] = {}
                if "relations" not in senses[inverseSource]:
                    senses[inverseSource]["relations"] = {}
                if inverseReltype not in senses[inverseSource]["relations"]:
                    senses[inverseSource]["relations"][inverseReltype] = []
                senses[inverseSource]["relations"][inverseReltype].append(inverseTarget)
        elif name == "SynsetRelation":
            reltype = attrs.getValue("relType")
            target = attrs.getValue("target")
            if "relations" not in synsets[self.currentSynset]:
                synsets[self.currentSynset]["relations"] = {}
            if reltype not in synsets[self.currentSynset]["relations"]:
                synsets[self.currentSynset]["relations"][reltype] = []
            synsets[self.currentSynset]["relations"][reltype].append(target)
            # now add the inverse relation if applicable
            if reltype in inverseRelations:
                inverseSource = target
                inverseTarget = self.currentSynset
                inverseReltype = inverseRelations[reltype]
                if inverseSource not in synsets:
                    synsets[inverseSource] = {}
                if "relations" not in synsets[inverseSource]:
                    synsets[inverseSource]["relations"] = {}
                if inverseReltype not in synsets[inverseSource]["relations"]:
                    synsets[inverseSource]["relations"][inverseReltype] = []
                synsets[inverseSource]["relations"][inverseReltype].append(inverseTarget)

    def endElement(self, name):
        pass

    def characters(self, content):
        if self.inDefinition:
            synsets[self.currentSynset]["gloss"] = synsets[self.currentSynset]["gloss"] + content.strip()

def POS_DISPLAY(pos):
    return SText("(" + pos + ") ", font="Helvetica 12", text_color="red")

def GLOSS_DISPLAY(gloss):
    return SText(gloss, font="Helvetica 12")


def Collapsible(layout, key, title='', arrows=("–", "+"), collapsed=False):
    """
    User Defined Element
    A "collapsable section" element. Like a container element that can be collapsed and brought back
    :param layout:Tuple[List[sg.Element]]: The layout for the section
    :param key:Any: Key used to make this section visible / invisible
    :param title:str: Title to show next to arrow
    :param arrows:Tuple[str, str]: The strings to use to show the section is (Open, Closed).
    :param collapsed:bool: If True, then the section begins in a collapsed state
    :return:sg.Column: Column including the arrows, title and the layout that is pinned
    """
    global linkList
    linkList.append(key + "-BUTTON-")
    linkList.append(key + "-TITLE-")
    return sg.Column([[sg.T("          " + (arrows[1] if collapsed else arrows[0]), enable_events=True, k=key+'-BUTTON-', font="Helvetica 14 bold"),
                       sg.T(title, font="Helvetica 12 italic", enable_events=True, key=key+'-TITLE-')],
                      [sg.pin(sg.Column(layout, key=key, visible=not collapsed, metadata=arrows))]], pad=(0,0))

def SText(text, *positionalArgs, **keywordArgs):
    return sg.InputText(text, *positionalArgs, **keywordArgs, size=(len(text)+1, None),  pad=0, use_readonly_for_disable=True, disabled=True, disabled_readonly_background_color="white", border_width=0)

def LText(text, k, *positionalArgs, **keywordArgs):
    global linkList
    linkList.append(k)
    return [sg.Text("►", key=k, enable_events = True, pad=0, border_width=0, font="Helvetica 12 bold", text_color="blue"), SText(text, *positionalArgs, **keywordArgs)]

def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

# ==================================================================================

WINDOW_TITLE = 'LiveLanguage Lexicon View'
posNames = {"n": "Noun", "v": "Verb", "a": "Adjective", "r": "Adverb"}
inverseRelations = {"hyponym": "hypernym", "hypernym": "hyponym", "mero_part": "holo_part", "holo_part": "mero_part", "mero_substance": "holo_substance", "holo_substance": "mero_substance", "mero_member": "holo_member", "holo_member": "mero_member", "subevent": "is_subevent_of", "is_subevent_of": "subevent", "attribute": "attribute", "metaphorically_related_concept": "metaphorically_related_concept", "metonymically_related_concept": "metonymically_related_concept", "is_aspect_of": "has_aspect", "has_aspect": "is_aspect_of", "metonym": "metonym", "cognate": "cognate", "derivation": "derivation", "antonym": "antonym", "also": "also", "similar": "similar"}
bias = (0, 0)
lemmas = {}
senses = {}
synsets = {}
relations = {}
langName = []
langCode = []
langPublisher = []
langDescription = []
langProv = []


if len(sys.argv) < 2:
    print("An LMF/XML file is needed as input argument! Exiting.")
    sys.exit(1)

    
file = sys.argv[1]

fn = open(file, encoding="utf8")
parser = xml.sax.make_parser()
handler = SaxHandler()
parser.setContentHandler(handler)
parser.parse(fn) # TODO: validation


if len(langName)==0:
    print("No Lexicon found in input file, Exiting")
    sys.exit(1)

sg.change_look_and_feel('LightGrey1')


layoutTop = [
                [sg.Text('Multi-LiveLanguage Lexicon  Hub:[' + langCode[0] + ']', font='Verdana 14 bold'), sg.Text('Language to translate to:', font='Verdana 12'), sg.OptionMenu(langName, key="-Selected language-")],
                [sg.Text('Word to search for:', font='Helvetica 12'), sg.InputText(key="wordinput", font='Helvetica 12',focus = True), sg.Button('Search Lexicon', bind_return_key = True)],
                [sg.Column([], key="content", size=(80,200))]
            ]
Lexicon_info_combo=sg.Combo(langName,enable_events=True,readonly=True,key="Lexicon_info")
layoutBottom = [sg.Text("Lexicon info:",font="Verdana 10"),Lexicon_info_combo,sg.Push(),sg.Button('Quit')]

#section1 = [[sg.Input('Input sec 1', key='-IN1-')]]

layout = [ layoutTop,
           [sg.Text(key='-OUTPUT-', font='Helvetica 14 bold')],
           [sg.VPush()],
           layoutBottom,
           #[Collapsible(section1, SEC1_KEY,  'Section 1', collapsed=True)]
         ]
            
window = sg.Window('LiveLanguage Lexicon View', layout, resizable = True,finalize=True)
window.maximize()
# Event Loop to process "events" and get the "values" of the inputs
while True:
    linkList = []
    
    event, values = window.read()
    if event == sg.WIN_CLOSED or event == 'Quit': # if user closes window or clicks cancel
        break
    elif event == "Lexicon_info":
        i=langName.index(values["Lexicon_info"])
        sg.popup_scrolled(langName[i] + ' LiveLanguage Lexicon [' + langCode[i] + ']', "", "Description: " + langDescription[i], "", "Publisher: " + langPublisher[i], "", "Data sources:\n" + " - " + "\n - ".join(langProv[i]), title="Lexicon Info")
        continue
    elif event.startswith("LEMMA"):
        wordPostfix = event.split(":")[1]
        word = wordPostfix.split("_")[0] # remove postfix "_" and synset ID
    elif event.startswith("COLLAPSE_"):
        if event.endswith('-BUTTON-'):
            key = event[:-8]
        elif event.endswith('-TITLE-'):
            key = event[:-7]
        else:
            key = event
        window[key].update(visible=not window[key].visible)
        window[key + "-BUTTON-"].update("          " + (window[key].metadata[0] if window[key].visible else window[key].metadata[1]))

        contentSize = window["content"].get_size()
        newContentSize = (contentSize[0], contentSize[1] + 200)
        window["content"].set_size(newContentSize)

        # index=key.index('|')
        # column_key="column_" + key[9:index]

        # contentSize = window[column_key].get_size()
        # newContentSize = (contentSize[0], contentSize[1] + 200)
        # window[column_key].set_size(newContentSize)

        # commen

        continue
    else:
        word = values["wordinput"].strip()

    # TODO: escape dangerous characters
    word = word.replace('"', '')
    
    if word not in lemmas and not word == "":
        window["-OUTPUT-"].update('“' + word + '” not found!')
        continue
    contentByPos = {}
    window.set_cursor("watch")
    if word == "":
        pass
    else:
        for wordAttrs in lemmas[word]:
            sense = senses[wordAttrs["senseId"]]
            pos = sense["pos"]
            relsByType = {}
            # find all sense relations
            if "relations" in sense:
                senseRelations = sense["relations"] 
                for reltype in senseRelations: 
                    for target in senseRelations[reltype]: 
                        targetSense = senses[target] 
                        if reltype not in relsByType: 
                            relsByType[reltype] = [] 
                        relsByType[reltype].append(targetSense)
            synsetId = sense["synsetId"]
            if not synsetId:
                print(word + " not found.")
                sys.exit(0)
            synset = synsets[synsetId]
            if "relations" in synset:
                synRelations = synset["relations"]
                for reltype in synRelations:
                    for target in synRelations[reltype]:
                        targetSynset = synsets[target]
                        if reltype not in relsByType:
                            relsByType[reltype] = []
                        relsByType[reltype].append(targetSynset)
            if pos not in contentByPos:
                contentByPos[pos] = []
            content = {}
            content["gloss"] = synset["gloss"]
            content["relations"] = relsByType
            content["synsetId"] = synsetId
            content["lemmas"] = synsets[synsetId]["lemmas"]
            contentByPos[pos].append(content)
    layoutBody = []

    for pos in contentByPos:
        layoutBody.append([sg.Text(posNames[pos], font='Helvetica 12 bold')])

        for entry in contentByPos[pos]:

            layoutRow = []
            entry_layout=[[]]
            translated_layoutRow=[]
            translated_layout=[[]]

            lemmaList = ", ".join(entry["lemmas"])
            lemmaList.strip()

            wraplength=(window.size[0]/(2*11))
            if wraplength<5:
                wraplength=5

            for line in textwrap.wrap(lemmaList, wraplength):
                layoutRow = []
                layoutRow.append(SText(line, font="Helvetica 12 bold", text_color="blue"))
                entry_layout.append(layoutRow)

            #debug
            # if layoutRow[0].Size[0]>len(lemmaList)+1:
            #     layoutRow.append(GLOSS_DISPLAY("b"))
            # layoutRow.append(GLOSS_DISPLAY("a"))
            
            wraplength=int(window.size[0]/(2*10)-14)
            if wraplength<5:
                wraplength=5

            for line in textwrap.wrap(entry["gloss"],wraplength):
                
                layoutRow = []
                layoutRow.append(GLOSS_DISPLAY(line))
                entry_layout.append(layoutRow)


            lexical_gap=False
            tranlation_present=False
            same_language=False
            translated_synsetId=""
            if not values["-Selected language-"] not in langName:

                synset_language=langName[0]
                middle_term=""
                if synsets[entry["synsetId"]]["ili"][-1] == 'n' or synsets[entry["synsetId"]]["ili"][-1] =='v' or synsets[entry["synsetId"]]["ili"][-1] =='a' or synsets[entry["synsetId"]]["ili"][-1] =='r':
                    middle_term=entry["synsetId"]
                else:
                    i=0
                    while True:
                        if entry["synsetId"][i]=='-':
                            break
                        i+=1

                    for code in langCode:
                        if entry["synsetId"][0:i]==code:
                            j=langCode.index(code)
                            synset_language=langName[j]
                            break
                        
                    middle_term=synsets[entry["synsetId"]]["ili"]
                if synset_language==values["-Selected language-"]:

                    same_language=True

                else:
                    
                    if values["-Selected language-"]==langName[0]:
                        translated_synsetId=middle_term
                    else:
                        j=langName.index(values["-Selected language-"])
                        target_code=langCode[j]

                        if target_code in synsets[middle_term]:
                            translated_synsetId=synsets[middle_term][target_code]
                        else: 
                            print("word not present in target language")
                            lexical_gap=True
                    
                    #print("translation: "+translated_synsetId)
                    if translated_synsetId != "":
                        if  "lemmas" in synsets[translated_synsetId]:

                            translated_lemmaList=", ".join(synsets[translated_synsetId]["lemmas"])

                            wraplength=(window.size[0]/(2*11))
                            if wraplength<5:
                                wraplength=5

                            for line in textwrap.wrap(translated_lemmaList, wraplength):
                                translated_layoutRow = []
                                translated_layoutRow.append(SText(line, font="Helvetica 12 bold", text_color="blue"))
                                translated_layout.append(translated_layoutRow)


                            wraplength=int(window.size[0]/(2*10))
                            if wraplength<5:
                                wraplength=5
                            
                            for line in textwrap.wrap(synsets[translated_synsetId]["gloss"],wraplength):
                            
                                translated_layoutRow = []
                                translated_layoutRow.append(GLOSS_DISPLAY(line))
                                translated_layout.append(translated_layoutRow)

                            tranlation_present=True

                            if "relations" in synsets[translated_synsetId]:
                                # print("synset_relations: "+str(synsets[translated_synsetId]["relations"]))

                                for relation_type in synsets[translated_synsetId]["relations"]:

                                    collapsableSection=[]
                                    for relation_target in synsets[translated_synsetId]["relations"][relation_type]:

                                        collapsableRow=[sg.Text("              ", font="Helvetica 12 bold")]
                                        lemmaList = synsets[relation_target]["lemmas"]
                                        initial_row_size=len("              ")
                                        
                                        for lemma in lemmaList:
                                            initial_row_size+=(len(lemma)+3)
                                            
                                            lemmaKey = "LEMMA:" + lemma + "_" + translated_synsetId + "_" + entry["synsetId"]
                                            collapsableRow = collapsableRow + LText(lemma, lemmaKey, enable_events = True, font='Helvetica 12 bold', text_color='blue')
                                        
                                        gloss = synsets[relation_target]["gloss"]


                                        if initial_row_size > window.size[0]/(5*10):
                                            wraplength=int((window.size[0]/(2*10)) - len("              "))

                                            collapsableSection.append(collapsableRow)
                                            for line in textwrap.wrap(gloss, wraplength):
                                                collapsableRow = []
                                                collapsableRow.append(GLOSS_DISPLAY("              " + "  " + line))
                                                collapsableSection.append(collapsableRow)

                                        else:    
                                            wraplength=int(window.size[0]/(2*10))-(initial_row_size)-2
                                            if wraplength<5:
                                                wraplength=5

                                            first=True
                                            for line in textwrap.wrap(gloss, wraplength):
                                                if first==False:
                                                    collapsableRow = []
                                                    collapsableRow.append(GLOSS_DISPLAY(' '*(initial_row_size-6)))
                
                                                first=False
                                                collapsableRow.append(GLOSS_DISPLAY(line))
                                                collapsableSection.append(collapsableRow)

                                    collapsableSectionKey = "COLLAPSE_" + translated_synsetId + "_" + entry["synsetId"] + "|" + relation_type
                                    translated_layout.append([Collapsible(collapsableSection, collapsableSectionKey, title=" " + relation_type + " relations", arrows=("–", "+"), collapsed = True)])

                            if "senses" in synsets[translated_synsetId]:

                                for sense in synsets[translated_synsetId]["senses"]:
                                    #print("synset_senses: "+sense)
                                    if "relations" in senses[sense]:
                                        for relation_type in senses[sense]["relations"]:
                                            #print(relation_type+str(senses[sense]["relations"][relation_type]))
                                            collapsableSection=[]

                                            for relation_target in senses[sense]["relations"][relation_type]:

                                                # print(relation_target)
                                                # print("translatedsynsetId: "+translated_synsetId)
                                                
                                                collapsableRow=[sg.Text("              ", font="Helvetica 12 bold")]
                                                lemma=senses[relation_target]["word"]
                                                lemmaKey = "LEMMA:" + lemma + "_" + relation_target + "_" + sense + "_" + translated_synsetId + "_" + entry["synsetId"]
                                                collapsableRow = collapsableRow + LText(lemma, lemmaKey, enable_events = True, font='Helvetica 12 bold', text_color='blue')
                                                gloss = synsets[senses[relation_target]["synsetId"]]["gloss"]

                                                wraplength=int(window.size[0]/(2*10))-len("              " + lemma)-1
                                                if wraplength<5:
                                                    wraplength=5

                                                first=True
                                                for line in textwrap.wrap(gloss, wraplength):
                                                    if first==False:
                                                        collapsableRow = []
                                                        collapsableRow.append(GLOSS_DISPLAY(' '*(len(lemma + "              ")-3)))
                
                                                    first=False
                                                    collapsableRow.append(GLOSS_DISPLAY(line))
                                                    collapsableSection.append(collapsableRow)
                                            
                                            collapsableSectionKey = "COLLAPSE_" + translated_synsetId + "_" + entry["synsetId"] + "|" + relation_type + sense
                                            translated_layout.append([Collapsible(collapsableSection, collapsableSectionKey, title=" " + relation_type + " relations for " + senses[sense]["word"], arrows=("–", "+"), collapsed = True)])
                            
                        else:
                            print("Not lexicalized, ",translated_synsetId)
                            lexical_gap=True
            
            
            if "relations" in synsets[entry["synsetId"]]:
                # print("synset_relations: "+str(synsets[entry["synsetId"]]["relations"]))

                for relation_type in synsets[entry["synsetId"]]["relations"]:

                    collapsableSection=[]
                    for relation_target in synsets[entry["synsetId"]]["relations"][relation_type]:

                        collapsableRow=[sg.Text("              ", font="Helvetica 12 bold")]
                        lemmaList = synsets[relation_target]["lemmas"]
                        initial_row_size=len("              ")
                                        
                        for lemma in lemmaList:
                            initial_row_size+=(len(lemma)+3)
                                            
                            lemmaKey = "LEMMA:" + lemma + "_" + entry["synsetId"]
                            collapsableRow = collapsableRow + LText(lemma, lemmaKey, enable_events = True, font='Helvetica 12 bold', text_color='blue')
                                        
                        gloss = synsets[relation_target]["gloss"]


                        if initial_row_size > window.size[0]/(5*10):
                            wraplength=int((window.size[0]/(2*11)) - len("              ")-10)

                            collapsableSection.append(collapsableRow)
                            for line in textwrap.wrap(gloss, wraplength):
                                collapsableRow = []
                                collapsableRow.append(GLOSS_DISPLAY("              " + "  " + line))
                                collapsableSection.append(collapsableRow)

                        else:    
                            wraplength=int(window.size[0]/(2*11))-(initial_row_size)-6
                            if wraplength<5:
                                wraplength=5

                            first=True
                            for line in textwrap.wrap(gloss, wraplength):
                                if first==False:
                                    collapsableRow = []
                                    collapsableRow.append(GLOSS_DISPLAY(' '*(initial_row_size-6)))
                
                                first=False
                                collapsableRow.append(GLOSS_DISPLAY(line))
                                collapsableSection.append(collapsableRow)

                    collapsableSectionKey = "COLLAPSE_" + "_" + entry["synsetId"] + "|" + relation_type
                    entry_layout.append([Collapsible(collapsableSection, collapsableSectionKey, title=" " + relation_type + " relations", arrows=("–", "+"), collapsed = True)])

            if "senses" in synsets[entry["synsetId"]]:

                for sense in synsets[entry["synsetId"]]["senses"]:
                    # print("synset_sense: " + senses[sense]["word"] + " - " + sense)
                    if "relations" in senses[sense]:
                        for relation_type in senses[sense]["relations"]:
                            # print(relation_type+str(senses[sense]["relations"][relation_type]))
                            collapsableSection=[]

                            for relation_target in senses[sense]["relations"][relation_type]:

                                # print(relation_target)
                                # print("translatedsynsetId: "+translated_synsetId)
                                                
                                collapsableRow=[sg.Text("              ", font="Helvetica 12 bold")]
                                lemma=senses[relation_target]["word"]
                                lemmaKey = "LEMMA:" + lemma + "_" + relation_target + "_" + sense + "_" + entry["synsetId"]
                                collapsableRow = collapsableRow + LText(lemma, lemmaKey, enable_events = True, font='Helvetica 12 bold', text_color='blue')
                                gloss = synsets[senses[relation_target]["synsetId"]]["gloss"]

                                wraplength=int(window.size[0]/(2*11))-len("              " + lemma)-10
                                if wraplength<5:
                                    wraplength=5

                                first=True
                                for line in textwrap.wrap(gloss, wraplength):
                                    if first==False:
                                        collapsableRow = []
                                        collapsableRow.append(GLOSS_DISPLAY(' '*(len(lemma + "              ")-3)))
                
                                    first=False
                                    collapsableRow.append(GLOSS_DISPLAY(line))
                                    collapsableSection.append(collapsableRow)
                                            
                            collapsableSectionKey = "COLLAPSE_" + entry["synsetId"] + "|" + relation_type + sense
                            entry_layout.append([Collapsible(collapsableSection, collapsableSectionKey, title=" " + relation_type + " relations for " + senses[sense]["word"], arrows=("–", "+"), collapsed = True)])
            # if entry["relations"]:
            #     for reltype in entry["relations"]:
            #         collapsableSection = []
            #         for rel in entry["relations"][reltype]:
            #             layoutRow = [sg.Text("              ", font="Helvetica 12 bold")]

            #             initial_row_size=len("              ")

            #             if "lemmas" in rel:
            #                 # it is a synset relation
            #                 lemmaList = rel["lemmas"]
            #             else:
            #                 # it is a sense relation
            #                 lemmaList = [rel["word"]] # only one word for a sense relation!
            #             for lemma in lemmaList:

            #                 if initial_row_size+len(lemma)+3 > window.size[0]/(2.3*10)-10:

            #                     collapsableSection.append(layoutRow)
            #                     layoutRow=[]
            #                     layoutRow.append(sg.Text("              ", font="Helvetica 12 bold"))
            #                     initial_row_size=len("              ")

            #                 initial_row_size+=len(lemma)+3
            #                 lemmaKey = "LEMMA:" + lemma + "_" + entry["synsetId"]
            #                 layoutRow = layoutRow + LText(lemma, lemmaKey, enable_events = True, font='Helvetica 12 bold', text_color='blue')

                            

            #             if "gloss" in rel:
            #                 # it is a synset relation
            #                 gloss = rel["gloss"]
            #             else:
            #                 # it is a sense relation
            #                 gloss = synsets[rel["synsetId"]]["gloss"]

            #             if initial_row_size > window.size[0]/(5*10):

            #                 wraplength=int((window.size[0]/(2*10)) - len("              ")-14)
            #                 if wraplength<5:
            #                     wraplength=5

            #                 collapsableSection.append(layoutRow)
            #                 for line in textwrap.wrap(gloss, wraplength):
            #                     layoutRow = []
            #                     layoutRow.append(GLOSS_DISPLAY("              " + "  " + line))
            #                     collapsableSection.append(layoutRow)

            #             else:    
            #                 wraplength=int(window.size[0]/(2*11))-(initial_row_size+14)
            #                 if wraplength<5:
            #                     wraplength=5

            #                 first=True
            #                 for line in textwrap.wrap(gloss, wraplength):
            #                     if first==False:
            #                         layoutRow = []
            #                         layoutRow.append(GLOSS_DISPLAY(' '*(initial_row_size-6)))
                
            #                     first=False
            #                     layoutRow.append(GLOSS_DISPLAY(line))
            #                     collapsableSection.append(layoutRow)

            #         collapsableSectionKey = "COLLAPSE_" + entry["synsetId"] + "|" + reltype
            #         entry_layout.append([Collapsible(collapsableSection, collapsableSectionKey, title=" " + reltype + " relations", arrows=("–", "+"), collapsed = True)])
    
            translated_column_key=""
            if lexical_gap:
                #needs implementation
                Lexical_gap_button=sg.Button("Add word")
                translated_layout.append([Lexical_gap_button])
            elif not (same_language or not tranlation_present):
                #needs implementation
                Correction_button_translation=sg.Button("Correct word")
                translated_layout.append([Correction_button_translation])

            #needs implementation
            Correction_button=sg.Button("Correct word")
            entry_layout.append([Correction_button])
            
            if translated_synsetId!="":
                translated_column_key="column_"+translated_synsetId+"_"+entry["synsetId"]
            
            translated_column=sg.Column(translated_layout, key = translated_column_key, vertical_alignment="top", pad=((0,0),(3,10)))
            
            entry_layout.append([sg.Sizer(window.size[0]/2 + 6, 0)])
            entry_column=sg.Column(entry_layout, key="column_" + entry["synsetId"], vertical_alignment="top", pad=((0,0),(3,10)))
            
            total_column=[entry_column]
            total_column.append(translated_column)
            layoutBody.append(total_column)
                    

    layoutBody = [sg.Column(layoutBody, scrollable = True, key="content", expand_x = True, expand_y = True,vertical_scroll_only=True)] # size=window["content"].Size
    
    Lexicon_info_combo=sg.Combo(langName,enable_events=True,readonly=True,key="Lexicon_info")
    layoutBottom = [sg.Text("Lexicon info:",font="Verdana 10"),Lexicon_info_combo,sg.Push(),sg.Button('Quit')]
    newLayout = [
                 [sg.Text('Multi-LiveLanguage Lexicon  Hub:[' + langCode[0] + ']', font='Verdana 14 bold'), sg.Text('Language to translate to:', font='Verdana 12'), sg.OptionMenu(langName, key="-Selected language-",default_value=values["-Selected language-"])],
                 [sg.Text('Word to search for:', font='Helvetica 12'), sg.InputText(key="wordinput", font='Helvetica 12', focus=True), sg.Button('Search Lexicon', bind_return_key = True)], 
                 [sg.Text(key='-OUTPUT-', font='Helvetica 14 bold')],
                 layoutBody,
                 layoutBottom
                ]
    currentLocation = window.CurrentLocation()
    adjustedLocation = (currentLocation[0] - bias[0], currentLocation[1] - bias[1])
    newWindow = sg.Window(WINDOW_TITLE, newLayout, location = adjustedLocation, resizable = True, finalize = True)
    newWindow.size = window.size
    newLocation = newWindow.CurrentLocation()
    if not newLocation == currentLocation:
        # window is migrating due to titlebar size: compensate it
        bias = (newLocation[0] - currentLocation[0], newLocation[1] - currentLocation[1])
    window.close()
    window = newWindow
    window["wordinput"].update(word)
    for linkKey in linkList:
        
        window[linkKey].set_cursor("hand2")
    window.set_cursor("arrow")
    window["-OUTPUT-"].update('“' + word + '”')

window.close()