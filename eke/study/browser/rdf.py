# encoding: utf-8
# Copyright 2009 California Institute of Technology. ALL RIGHTS
# RESERVED. U.S. Government Sponsorship acknowledged.

'''
EKE Studies: RDF ingest for study folders and their protocols.
'''

from Acquisition import aq_inner
from eke.knowledge.browser.rdf import IngestHandler, KnowledgeFolderIngestor, CreatedObject, RDFIngestException, Results
from eke.knowledge.browser.utils import updateObject
from eke.study import ProjectMessageFactory as _
from eke.study.interfaces import IProtocol
from plone.i18n.normalizer.interfaces import IIDNormalizer
from Products.CMFCore.utils import getToolByName
from rdflib import ConjunctiveGraph, URLInputSource
from zope.component import queryUtility

class StudyFolderIngestor(KnowledgeFolderIngestor):
    '''Study folder ingestion.'''
    def __call__(self, rdfDataSource=None):
        '''Ingest and render a results page'''
        context = aq_inner(self.context)
        catalog = getToolByName(context, 'portal_catalog')
        if rdfDataSource is None:
            rdfDataSource = context.rdfDataSource
        if not rdfDataSource:
            raise RDFIngestException(_(u'This folder has no RDF data source URL.'))
        normalizerFunction = queryUtility(IIDNormalizer).normalize
        graph = ConjunctiveGraph()
        graph.parse(URLInputSource(rdfDataSource))
        statements = self._parseRDF(graph)
        createdObjects = []
        handler = StudyHandler()
        for uri, predicates in statements.items():
            results = catalog(identifier=uri, object_provides=IProtocol.__identifier__)
            objectID = handler.generateID(uri, predicates, normalizerFunction)
            if len(results) == 1 or objectID in context.keys():
                # Existing protocol. Update it.
                if objectID in context.keys():
                    p = context[objectID]
                else:
                    p = results[0].getObject()
                oldID = p.id
                updateObject(p, uri, predicates, context)
                newID = handler.generateID(uri, predicates, normalizerFunction)
                if oldID != newID:
                    # Need to update the object ID too
                    p.setId(newID)
                created = [CreatedObject(p)]
            else:
                if len(results) > 1:
                    # More than one? WTF? Nuke 'em all.
                    context.manage_delObjects([p.id for p in results])
                # New protocol. Create it.
                title = handler.generateTitle(uri, predicates)
                created = handler.createObjects(objectID, title, uri, predicates, statements, context)
            for obj in created:
                obj.reindex()
            createdObjects.extend(created)
        self.objects = createdObjects
        self._results = Results(self.objects, warnings=[])
        return self.renderResults()

class StudyHandler(IngestHandler):
    '''Handler for ``Protocol`` objects.'''
    def generateID(self, uri, predicates, normalizerFunction):
        return str(uri.split('/')[-1]) + '-' + super(StudyHandler, self).generateID(uri, predicates, normalizerFunction)
    def createObjects(self, objectID, title, uri, predicates, statements, context):
        p = context[context.invokeFactory('Protocol', objectID)]
        updateObject(p, uri, predicates, context)
        return [CreatedObject(p)]

